CHANGELOG
=========

すべての注目すべき変更点を記録します。This project adheres to "Keep a Changelog" と Semantic Versioning に準拠します。

フォーマット:
- Unreleased: 開発中の変更（このリリース時点では未記載）
- 各リリースは日付付きで記載

Unreleased
----------

なし

0.1.0 - 2026-04-01
------------------

最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境・設定管理
  - Settings クラスを提供し、環境変数から各種設定を取得（src/kabusys/config.py）。
    - 必須設定を取得する _require()（未設定時は ValueError）。
    - デフォルト値や型変換（Path, float）を備えたプロパティ群（DB パス、監視閾値、ログレベル、環境種別など）。
    - 有効な環境値・ログレベルのバリデーションを実装（development / paper_trading / live、DEBUG/INFO/...）。
  - .env 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索し、.env と .env.local を自動的に読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ:
    - コメント・空行無視、export KEY=val 形式対応、クォート（シングル/ダブル）とバックスラッシュエスケープ対応、インラインコメントの扱い等の堅牢な実装。

- AI: ニュース NLP / レジーム検出
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメント（-1.0〜1.0）を評価。
    - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたり記事数と文字数のトリム制限を実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results フォーマット、コード照合、スコア数値化、±1.0 クリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - DuckDB の executemany 空リスト制約を考慮した安全な DB 書き込み（部分置換: DELETE -> INSERT）。
    - テスト容易性のため _call_openai_api を差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を算出。
    - prices_daily と raw_news を参照して ma200_ratio と macro_sentiment を計算。
    - OpenAI 呼び出しに対するリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - モジュール間結合を避けるため、OpenAI 呼び出し実装は news_nlp のものと独立。

- Data: カレンダー、ETL、パイプライン
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバック（週末は非営業日）。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ calendar_update_job を実装。
    - バックフィル、健全性チェック（未来日付の異常検出）、探索上限（日数）の設定で安全性を確保。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得・保存・品質チェック（quality モジュール経由）を想定した ETLResult データクラスを実装。
    - ETLResult.to_dict() により品質問題を辞書化して監査ログ等に利用可能。
    - J-Quants クライアント（jquants_client）経由での取得と保存の呼び出し点を整理。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
    - ETL の設計方針（バックフィル、部分失敗での既存スコア保護など）を実装。

- Research: ファクター計算・特徴量探索
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB SQL で実装し、(date, code) 単位の dict リストを返す。
    - データ不足時の None 処理やログ出力。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman ランク相関）calc_ic、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - 外部ライブラリ非依存（標準ライブラリのみ）、DuckDB 接続を前提。

- パッケージ API の整備
  - ai.__init__.py, research.__init__.py で主要関数をエクスポート（score_news, score_regime, calc_*, zscore_normalize 等）。
  - data/etl.py で ETLResult を再エクスポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キー（OPENAI_API_KEY）や外部 API トークンは必須であり、API 呼び出しを行う関数（score_news, score_regime 等）はキー未設定時に ValueError を送出して操作を防止。
- 必要な環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 実装上の重要事項
- ルックアヘッドバイアス対策: AI / リサーチ関連の処理は内部で datetime.today()/date.today() を参照せず、呼び出し側が target_date を渡す設計。
- DuckDB 互換性:
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）点を考慮した実装。
  - 一部テーブル存在チェックや日付変換ユーティリティを実装。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode（response_format={"type":"json_object"}）を使用。
  - API の失敗ケースに対してリトライ（指数バックオフ）を行い、最終的にはフォールバック値（例: macro_sentiment=0.0）で継続するフェイルセーフ設計。
  - テスト容易性のため _call_openai_api をパッチで差し替えられるようにしている。
- DB 書き込みの冪等性:
  - AI スコア・レジーム等は既存レコードを削除してから INSERT することで冪等に格納。
  - ai_scores の部分書き換えにより、API 部分失敗時に他銘柄の既存スコアを保護する。
- .env パーサの挙動:
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い（スペース直前の # でコメント扱い）に対応。
  - .env.local は .env を上書きする（override=True）。

Breaking Changes
- 初回リリースのため該当なし。

References / TODO
- strategy, execution, monitoring モジュールは __all__ に含まれるが本リリースでは詳細ファイルが提示されていません（今後追加予定）。
- 一部ユーティリティ（例: kabusys.data.stats や jquants_client, quality モジュール）は本リリースと組み合わせて使用する前提で、外部実装・モックが必要です。

Contributing
- バグ報告・機能要望は Issue を通じてお願いします。設計方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフ）を尊重する実装を歓迎します。

----- 

以上が v0.1.0 の変更履歴（初回リリース）です。必要であれば、個別ファイルごとの詳細変更履歴や例示的な使用例（設定例、DB スキーマ想定、API レスポンスフォーマット）も追記できます。どの程度の詳細を希望しますか？