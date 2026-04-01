# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

全般
- リポジトリ初期バージョンを追加（バージョン 0.1.0）。
- パッケージ名: kabusys
- 主要言語: Python（DuckDB、OpenAI API クライアントを想定）
- 設計上の共通方針:
  - ルックアヘッドバイアスを避けるため、datetime.today()/date.today() を直接参照しない設計。
  - 外部／本番 API（注文実行など）への依存を最小化し、データ処理・研究系処理は安全にローカル DB（DuckDB）で完結することを意図。
  - OpenAI 呼び出しは JSON Mode を使用し、堅牢なバリデーション・リトライ戦略を実装。
  - テスト容易性のため一部内部関数のモック差し替えポイントを提供。

[0.1.0] - 2026-04-01
Added
- パッケージエントリポイント
  - src/kabusys/__init__.py: パッケージバージョン (__version__ = "0.1.0") と公開サブパッケージ一覧を定義。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイル（.env, .env.local）と OS 環境変数からの設定読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に自動ロードを行う。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーを実装（コメント行、export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメント処理などに対応）。
    - Settings クラスを提供し、主要設定項目をプロパティとして公開（J-Quants、kabuステーション、Slack、DB パス、監視閾値、実行環境判定など）。
    - 設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等の許容値チェック）と必須環境変数の必須チェック（_require）を実装。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事（raw_news）を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価を行い ai_scores テーブルへ保存する機能（score_news）。
    - 時間ウィンドウは JST ベースで「前日 15:00 〜 当日 08:30」（UTC 変換済）を採用。calc_news_window を提供。
    - バッチ処理（1リクエスト最大 20 銘柄）、1銘柄あたりの記事および文字数の上限トリム、リトライ（429/ネットワーク/5xx）と指数バックオフを実装。
    - API レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score 検証、数値性チェック）とスコアクリッピング（±1.0）。
    - フェイルセーフ: API 失敗やパース失敗時は当該チャンクをスキップし、致命的例外を上げずに継続（部分書き込みを保護するため書き込み前に該当コードのみ DELETE してから INSERT）。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock.patch で差し替え）に設計。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次市場レジーム（bull / neutral / bear）を判定する機能（score_regime）。
    - ma200 比率計算（過去 200 日分、target_date 未満のデータのみ使用）とマクロニュース抽出（マクロキーワードでフィルタ）を実装。
    - OpenAI 呼び出しは JSON モードで行い、最大リトライ回数やバックオフ、API 種別エラー（status_code に基づく 5xx 判定）に応じた挙動を実装。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み。
    - テスト可能性のため _call_openai_api の差し替えが可能。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - 営業日判定・前後営業日取得・期間内営業日列挙・SQ日判定関数を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の market_calendar が未存在・未取得時は曜日ベースのフォールバック（土日休み）を使用する一貫したロジック。
    - calendar_update_job により J-Quants から差分取得 → save（jquants_client 経由）を行い、バックフィルと健全性チェック（未来日過大はスキップ）を組み込み。
    - 最大探索日数やバックフィル日数、lookahead などの定数を定義。

  - src/kabusys/data/pipeline.py および src/kabusys/data/etl.py:
    - ETL パイプラインのインターフェースを追加。
    - ETLResult dataclass を実装（取得件数・保存件数・品質チェック結果・エラーの集約）。to_dict メソッドでシリアライズ可能。
    - 差分取得、バックフィル、品質チェック統合の設計方針を記述（jquants_client, quality モジュールを利用する想定）。
    - 内部ユーティリティで DuckDB テーブル存在確認や最大日付取得を実装（ETL での利用を想定）。

  - src/kabusys/data/__init__.py:
    - ETLResult を再エクスポート（etl.py 経由）。

  - jquants_client（使用想定）との連携ポイントを確保（calendar_update_job, pipeline からの呼び出し）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py:
    - ファクター計算機能を追加（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Volatility/Liquidity: 20 日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - Value: raw_financials から最新財務を取得し PER、ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を実装。
    - calc_forward_returns は複数ホライズンをサポート（デフォルト [1,5,21]）。horizons の妥当性検証あり。
    - calc_ic はスピアマンのランク相関を ranking を通じて算出し、サンプル数不足や分散ゼロを安全に処理。
    - feature_exploration パッケージで zscore_normalize（data.stats 由来）などを再エクスポート。

- その他
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py: 主要関数を __all__ にてエクスポートしパッケージ API を整理。
  - テスト・運用を意識したログ出力（logger）と詳細な警告メッセージが各モジュールに追加されている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

補足（実装上の注意）
- OpenAI API 利用:
  - モデルは gpt-4o-mini を想定。JSON Mode を利用するためレスポンスパースに関するフォールバック処理を多数実装。
  - API キーは関数引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照する。
  - リトライ方針、5xx 判定、レスポンス検証により、API 側の問題が研究・レジーム判定処理全体を止めないようフェイルセーフ化。

- DuckDB / DB 書き込み:
  - 複数 DB 操作は明示的なトランザクション（BEGIN / COMMIT / ROLLBACK）で行い、部分書き込み対策を実施。
  - DuckDB の executemany の制約（空リスト不可）を考慮した実装上の注意あり。

今後の提案（実装候補・改善点）
- テスト用のユーティリティ（テストDB、OpenAI モックヘルパー）の同梱。
- OpenAI レスポンスパースの更なる堅牢化（スキーマ検証ライブラリの導入検討）。
- ETL のスケジューリング・監視ジョブ（Slack 通知フックなど）の追加。
- レジーム判定やニューススコアのヒストリカル検証用 CLI / Notebook サポート。

--- 
（この CHANGELOG はコードベースの読み取りに基づき推測して作成しています。実際のリリースノートはコミット履歴やリリース条件に合わせて調整してください。）