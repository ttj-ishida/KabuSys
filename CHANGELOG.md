# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、Semantic Versioning を使用しています。
（https://keepachangelog.com/ja/1.0.0/）

## [Unreleased]

## [0.1.0] - 2026-03-28
初期リリース。

### Added
- パッケージ基盤
  - パッケージ初期化ファイルを追加（kabusys v0.1.0）。公開 API: data, strategy, execution, monitoring。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数を取り扱う設定モジュールを追加。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）による .env / .env.local 自動読み込み機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 独自の .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の取り扱いなど）。
  - Settings クラスを提供。必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）の取得、環境（development / paper_trading / live）とログレベルのバリデーション、データベースパス（DuckDB/SQLite）設定等を一元管理。

- データプラットフォーム関連（kabusys.data）
  - calendar_management モジュールを追加：
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）。
    - SQ 日判定（is_sq_day）。
    - DB 未取得時の曜日ベースフォールバックや最大探索日数保護、健全性チェック等の実装。
  - ETL パイプライン（kabusys.data.pipeline）を追加：
    - 差分取得ロジック、バックフィル、品質チェックのフレームワークを実装。
    - ETLResult データクラスを提供（処理結果集約、品質問題とエラーの集計、辞書変換機能）。
  - ETL の公開インターフェースを etl モジュールで再エクスポート（ETLResult）。

- AI / NLP（kabusys.ai）
  - news_nlp モジュールを追加：
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（ai_scores テーブル）を算出・書き込み。
    - タイムウィンドウ計算（calc_news_window）、トリミング（記事数・文字数上限）、チャンク処理（最大 20 銘柄 / チャンク）、JSON Mode を用いたレスポンスバリデーション、クリップ処理（±1.0）、エクスポネンシャルバックオフによるリトライ、部分書き換え（DELETE→INSERT）での冪等保存を実装。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
  - regime_detector モジュールを追加：
    - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - DuckDB からの価格・ニュース取得、OpenAI 呼び出し（gpt-4o-mini）、フェイルセーフ（API 失敗時 macro_sentiment=0.0）、再試行・バックオフ、レジーム結果の冪等書き込みを実装。
    - 設計上の注意点としてルックアヘッドを防ぐため datetime.today()/date.today() を参照しない実装。

- Research（kabusys.research）
  - factor_research モジュールを追加：
    - Momentum (1M/3M/6M)、200日MA乖離、ATR（20日）、流動性指標（平均売買代金・出来高比率）、Value（PER・ROE）等のファクター計算を実装。
    - DuckDB SQL を使用した効率的な集計、データ不足時の None 処理、結果を (date, code) 単位の dict リストで返却。
  - feature_exploration モジュールを追加：
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応）、IC（Spearman の ρ）計算（calc_ic）、ランキング変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装を目指す。
  - research パッケージの __init__ で主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI キー等の必須シークレットは Settings 経由で取得する設計。環境変数の自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）にしてテストや安全運用を考慮。

### Notes / Design highlights
- ルックアヘッドバイアス防止：AI・レジーム・ETL・Research 系のモジュールは内部で datetime.today()/date.today() を参照せず、target_date を明示的に受け取る設計。
- DuckDB を分析用の主要なローカルデータストアとして利用。SQL と Python の併用で効率的に集計処理を実行。
- 外部 API 呼び出し（OpenAI / J-Quants）に対してはリトライ、バックオフ、フェイルセーフ（スコア 0.0 にフォールバック、部分書き換えで既存データ保護）を実装し、堅牢性を重視。
- データベース書き込みは可能な限り冪等（DELETE→INSERT, ON CONFLICT 相当）を意識。

### Breaking Changes
- なし（初期リリース）

---

今後の予定（例）
- strategy / execution / monitoring の具体実装、テストカバレッジ拡充、ドキュメント追加、CI/CD パイプライン整備。