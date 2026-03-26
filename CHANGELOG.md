CHANGELOG
=========

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。  

[保守方針の一例]
- バージョン番号は semver を想定しています（このリリースは初期バージョン）。
- 変更はカテゴリ別（Added, Changed, Fixed, Security 等）で記載します。

[0.1.0] - 2026-03-26
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージトップで __version__ を "0.1.0" として公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に特定するため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式やシングル／ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなしの場合は "#" 前がスペースまたはタブのときのみコメントとして扱う等、現実的な .env 記法を処理。
  - _load_env_file による上書き制御（override, protected）を実装し、OS 環境変数の保護をサポート。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV (development|paper_trading|live) と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のブールヘルパー

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む機能を追加。
  - 処理の主な特徴:
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB クエリに使用。
    - 1 銘柄あたり最大記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
    - バッチ処理（1 API コールで最大 20 銘柄）と指数的バックオフによる再試行（429/ネットワーク/タイムアウト/5xx 対象）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リストの検証、既知コードのみ採用、スコアの数値変換・有限性チェック）。
    - スコアは ±1.0 にクリップ。
    - DuckDB の互換性対応: executemany に空リストを渡さないガード。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - テスト容易性: OpenAI 呼び出し部分（_call_openai_api）は差し替え可能（unittest.mock.patch 推奨）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（'bull'/'neutral'/'bear'）を計算する機能を追加。
  - 処理の主な特徴:
    - マクロキーワードで raw_news のタイトルをフィルタし、最大 20 件を LLM に渡して macro_sentiment を取得。
    - LLM 呼び出しは gpt-4o-mini、JSON 出力を期待。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) の式で合成。閾値により bull/neutral/bear を決定。
    - 結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
  - OpenAI API 呼び出し関数は news_nlp と独立実装（モジュール結合を避ける設計）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダー（祝日・半日取引・SQ）の夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ヘルパーを実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - カレンダーデータ未取得時は曜日ベースでフォールバック（週末は非営業日）。
    - next/prev/get は DB に登録のある日付を優先し、未登録日は曜日フォールバックで一貫した結果を返す。探索上限を設定して無限ループを防止。
  - ETL パイプライン（pipeline, etl）:
    - ETLResult dataclass を公開（kabusys.data.etl 経由で再エクスポート）。ETL の実行結果（取得数・保存数・品質問題・エラー一覧など）を構造化して返す。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）などの設計方針を反映。
    - 内部で DuckDB 最大日付取得やテーブル存在チェックのユーティリティを提供。

- リサーチ機能（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を追加:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - いずれも結果は (date, code) をキーとする dict のリストで返却。データ不足時は None を返す方針。
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None) （デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman の ρ）
    - 榜率ランク変換: rank(values)
    - 統計サマリー: factor_summary(records, columns)
    - 実装は外部ライブラリに依存せず標準ライブラリ（DuckDB SQL + Python）で実装。

Changed
- 基本設計方針の明文化:
  - 全ての分析関数は datetime.today()/date.today() を内部で参照しない方針（ルックアヘッドバイアス防止）。すべて target_date を明示的に受け取る。
  - OpenAI 関連は再試行・フォールバックのポリシーを明確化（ネットワーク/429/5xx 等を対象に指数的バックオフ）。
  - DB 書き込みは可能な限り冪等に（DELETE してから INSERT、部分失敗時に他コードの既存スコアを保護）実装。

Fixed
- DuckDB 互換性を考慮した運用上の調整:
  - executemany に空リストを渡すと失敗する点を回避するガードを追加（score_news の書き込み処理等）。
- OpenAI レスポンス処理の堅牢化:
  - JSON mode でも前後に余計なテキストが混ざる場合に最外の {} を抽出して復元するロジックを追加（news_nlp の _validate_and_extract）。

Security
- API キー取り扱いの注意点を明記:
  - OpenAI API キーは api_key 引数で注入可能かつ環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を出すことで意図しない無認証呼び出しを防止。
  - .env 自動ロードで OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Implementation details
- OpenAI モデルはデフォルトで gpt-4o-mini を使用。
- news_nlp と regime_detector は共に OpenAI を使用するが、内部の _call_openai_api はそれぞれ独立実装（モジュール間でプライベート関数を共有しない設計）。
- ロギングは各モジュールで logger を使用しており、処理状況やフォールバックを詳細に記録する。
- DuckDB 接続を受け取り SQL と Python を組み合わせた実装が主（本リリースでは外部発注 API 等にはアクセスしない設計）。
- テスト容易性のため、OpenAI 呼び出し箇所（_call_openai_api）を unittest.mock.patch で差し替えられるようにしている。

Breaking Changes
- 初期リリースのため該当なし。

今後の予定（例）
- PBR・配当利回り等のバリューファクター拡張。
- 学習済みモデルや追加の信号（ニュースの本文解析やより高度な NLP）導入。
- ETL のスケジュール/監視用 CLI や Web ダッシュボードの追加。

---

この CHANGELOG はコードベースのコメント・ドキュメントと実装から推測して作成しています。詳細や追加の変更（外部モジュールの更新、API 仕様変更等）がある場合は随時更新してください。