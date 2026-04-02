# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
安定化後はセマンティックバージョニングを採用します。

- リリース日付の形式: YYYY-MM-DD
- 既知の不足点や設計上の注意は「注意事項」に記載します。

他の参照:
- リポジトリ比較リンク: (差分リンクをここに挿入)

## [Unreleased]
- （次回以降の変更をここに記載）

## [0.1.0] - 2026-04-02
初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な機能と設計方針は以下のとおりです。

### Added
- パッケージ初期化
  - kabusys パッケージの公開バージョンを 0.1.0 として追加。
  - __all__ に data, strategy, execution, monitoring を設定。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメントに対応。
  - OS 環境変数を保護するため .env 読み込み時の上書き制御（protected keys）を実装。
  - Settings クラスを提供し、以下の環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト: data/monitoring.db)
    - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - 設定は不足時に適切なエラー（ValueError）を投げる挙動を定義。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を読んで銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON モードで一括センチメントを取得。
    - バッチサイズ制御、1銘柄あたりの最大記事数・最大文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証・スコアクリッピング（±1.0）を実装し、得られたスコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT）。
    - APIキーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。対象ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して使用。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース N 件（最大 20 件）に対する LLM マクロセンチメント（重み 30%）を合成して market_regime テーブルに書き込む。
    - ma200 計算は target_date 未満のデータのみを使用（ルックアヘッド回避）。
    - OpenAI 呼び出しは独自実装で、失敗時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - レジームスコアはクリップされ、閾値により "bull"/"neutral"/"bear" を判定。
    - DB への書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）。例外発生時には ROLLBACK を試行。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar テーブルを基に営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に値がなければ曜日ベース（土日除外）でフォールバックする堅牢な実装。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ（calendar_update_job）を実装。バックフィル日数や健全性チェックを備える。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェックという設計方針に基づく骨子を実装（jquants_client 経由の保存、品質チェック収集などを想定）。
    - デフォルトのバックフィル日数・カレンダー先読みなどの定数を定義。

- 研究モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR/価格比、20日平均売買代金、出来高比を計算。欠損ハンドリングを実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を算出（EPS=0/欠損時は None）。
  - feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一度の SQL で取得する実装（horizons の入力バリデーションあり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが不足する場合は None を返す。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算するユーティリティ。
  - 研究ユーティリティは外部（pandas 等）に依存せず標準ライブラリと DuckDB のみで実装。

- ロギングと堅牢性
  - 各所で詳細な logger を配置。API失敗・パース失敗時は警告ログを出し、可能な限り処理を継続するフェイルセーフ設計を採用。
  - OpenAI 呼び出しや外部 API 呼び出しには再試行と指数バックオフを実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### 注意事項 / Known limitations
- OpenAI 関連機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。api_key を明示的に渡すことも可能です。
- news_nlp と regime_detector は gpt-4o-mini を前提にプロンプトと JSON Mode を使って実装されています。API の仕様変更によりパースロジックの調整が必要になる可能性があります。
- settings._require により一部環境変数は必須です。未設定時は ValueError を投げます（実行時に環境を整えてください）。
- ETL/pipeline や jquants_client, quality モジュールの具体的な実装（外部 API クライアント等）は想定されており、実環境での接続設定・認証情報の準備が必要です。
- DuckDB への executemany の制約（空リスト不可）など、環境依存の挙動に注意しています。詳細は各関数の docstring を参照してください。
- 本リリースは「コア機能の提供」が主目的で、CLI や運用自動化ツールは含まれていません。

---

今後の予定:
- モニタリング／実行（execution / monitoring）周りの実装拡充
- テストカバレッジの強化（特に OpenAI 呼び出しのモックを用いたユニットテスト）
- ドキュメント（ユーザー向けセットアップ手順、運用ガイド）の整備

もし CHANGELOG に追加してほしい項目（例えば特定のコミットや Issue の参照、貢献者の明記）があればお知らせください。