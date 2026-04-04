# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、リポジトリ内のコードから推測される変更・機能・設計上の注意点をまとめたものです。

注意: バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づきます。

## [Unreleased]

（現在のスナップショットは 0.1.0 の初期リリースとして記録されています。将来の変更はここに列挙してください。）

---

## [0.1.0] - 2026-04-04

### Added
- 初期リリース: 日本株自動売買 / データ分析プラットフォームのコアライブラリを追加。
  - パッケージ公開名: kabusys（__version__ = 0.1.0）。
  - 主要サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ により公開）。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - キーのパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD`=1 で無効化可能。
  - 主要設定値を Settings クラスで提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、OPENAI など）。
  - デフォルトDBパス（DUCKDB_PATH: data/kabusys.duckdb、SQLITE_PATH: data/monitoring.db）や監視フラグ関連の設定をプロパティで提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）へ問い合わせて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
  - タイムウィンドウの算出（前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 範囲）。
  - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたりの記事数・文字数制限（最大 10 記事 / 3000 文字）。
  - JSON Mode 出力を期待し、レスポンスを厳密にバリデーションして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
  - リトライ戦略: レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフ。
  - フェイルセーフ: API 呼び出し失敗やパース失敗時は該当チャンクをスキップして処理継続。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動、コード "1321"）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の market_regime を算出・保存。
  - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価を実装（最大 20 記事）。
  - レジームは score に基づき "bull" / "neutral" / "bear" にラベリング。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。API 失敗時は macro_sentiment=0.0 をフォールバック。
- 研究用ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20日）、流動性指標（20日平均売買代金・出来高比）や財務由来の PER / ROE を計算。
  - feature_exploration: 将来リターン（デフォルト: 1/5/21 営業日）計算、IC（Spearman ランク相関）算出、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
  - 実装は DuckDB に対する SQL と Python によるもので、外部 API や発注系操作を行わない方針。
- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day の提供。market_calendar が無い場合は曜日ベースでフォールバック。
  - pipeline / etl: ETLResult データクラスの公開。ETL パイプラインの差分取得・保存・品質チェックの実装方針を反映する基盤を追加。
  - 複数のユーティリティ関数（テーブル存在チェック、日付変換など）。
- ETL 結果型（kabusys.data.pipeline.ETLResult）
  - ETL 実行結果の構造化（fetched/saved カウント、品質問題リスト、エラーリスト、シリアライズ用 to_dict）。
- テスト容易性向上
  - OpenAI 呼び出しをラップした内部関数（_call_openai_api）をモック差し替え可能にし、テストでの注入を容易にしている。

### Changed
- （初期公開のため該当なし。実装は多くの安全設計とフェイルセーフを反映。）

### Fixed
- （初期公開のため該当なし。実装には各所でのエラーハンドリングとロールバック処理を含む。）

### Security
- OpenAI API キー取扱い
  - AI 機能（score_news, score_regime）は引数 api_key または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出するため、キーの管理に注意すること。
- 自動 .env 読み込みは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）にし、テストや CI での不慮の環境汚染を防止。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT を利用する設計方針）し、部分失敗時に既存データを保護する実装になっている。

### Design / Implementation notes
- ルックアヘッドバイアス防止:
  - AI/研究関係の関数は datetime.today() / date.today() を参照しない設計。常に外部から与えられる target_date を基準に処理。
  - prices_daily などの参照では target_date 未満または BETWEEN 範囲を明確に指定している。
- OpenAI 呼び出し:
  - gpt-4o-mini を用い、JSON mode（response_format={"type":"json_object"}）での受け取りを前提としている。レスポンスのバリデーションや JSON パースの堅牢化を実施。
  - リトライは指数バックオフ（最大回数設定あり）で、5xx / レート制限 / ネットワーク断などを考慮。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続を引数に受け、SQL ウェイトで計算を行う（パフォーマンス志向）。
  - DuckDB バージョン差異（executemany の空リスト不可やリスト型バインドの挙動）に配慮した実装。
- フェイルセーフ:
  - API の障害やレスポンスパース失敗時は基本的に処理を中断せず、影響範囲を限定（0/空辞書/デフォルト値でフォールバック）。
- ロギング:
  - 各モジュールで詳細なログ（info/debug/warning/exception）を出す設計。異常時はログで理由を追跡可能。

### Removed
- （初期公開のため該当なし。）

---

メモ:
- 環境変数の主なキー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
  - OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID,
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT,
  - KABUSYS_ENV, LOG_LEVEL
- OpenAI 関連: モデル名は gpt-4o-mini。JSON モードによる厳密な構造を想定しているため、モデル/API 仕様変更があった場合は互換性対応が必要。

（この CHANGELOG は、ソースコードの注釈・ドキュメント文字列・実装内容から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜修正してください。）