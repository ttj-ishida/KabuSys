# Changelog

すべての注目すべき変更履歴をここに記載します。本ファイルは「Keep a Changelog」仕様に準拠しています。  

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージ初期公開。バージョンは 0.1.0。
  - パブリックエクスポート: data, strategy, execution, monitoring を __all__ に定義（各モジュール群への拡張点を確保）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検索（配布後の動作を配慮）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装: コメント、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスにより設定値をプロパティで取得:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE Messaging: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値
    - 環境種別・ログレベル検証（KABUSYS_ENV は development/paper_trading/live を許容、LOG_LEVEL は標準レベルを検証）
  - 設定不足時は説明付き ValueError を送出する（必須キーの検出）。

- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX マーケットカレンダー操作機能を実装（market_calendar テーブル適用想定）。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - calendar_update_job: J-Quants API 経由で差分取得・バックフィルを行い冪等保存。
    - DB 未取得時の曜日ベースフォールバック、探索上限 (_MAX_SEARCH_DAYS) による安全策、健全性チェック（過度な将来日付のスキップ）を実装。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題・エラー集約）。
    - 差分更新・バックフィル・品質チェック設計に対応するためのユーティリティを実装。DuckDB 互換性（executemany の空リスト回避等）を考慮。

- 研究・ファクター分析 (src/kabusys/research)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20日平均売買代金、出来高比率の計算。
    - calc_value: PER, ROE（最新の raw_financials を用いる）。
    - DuckDB を使った SQL+Python 実装。外部の市場操作は行わない。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（指定営業日ホライズン）を計算（複数ホライズン対応、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。
    - rank, factor_summary: ランク変換・統計サマリー機能を提供。
  - research パッケージは zscore_normalize（data.stats 側）などと連携するための再エクスポートを整備。

- AI / NLP (src/kabusys/ai)
  - news_nlp.py:
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini + JSON Mode) を用いて銘柄単位のセンチメント（ai_score）を生成。
    - 時間ウィンドウ: JST 前日 15:00 〜 当日 08:30（内部は UTC naive で扱う calc_news_window を提供）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1 銘柄あたりの記事・文字数トリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx）およびフェイルセーフ（失敗時は該当チャンクをスキップして継続）。
    - DuckDB 向けの冪等書き込み（DELETE → INSERT）実装。部分失敗時に既存データの保護を考慮。
  - regime_detector.py:
    - score_regime: ETF 1321（日経225連動）について 200 日 MA 乖離（70%）とマクロセンチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出、OpenAI によるマクロセンチメント評価（gpt-4o-mini）、クリップ・スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - 設計上、ルックアヘッドバイアス防止（date 未満のデータのみ参照）や API 失敗時のフォールバック（macro_sentiment=0.0）を採用。
  - OpenAI 呼び出しにはテスト容易性を考慮し _call_openai_api を分離（unittest.mock.patch により差し替え可能）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記 / 実装上の設計判断（重要なポイント）
- ルックアヘッドバイアス防止: すべての「当日判定」系処理は内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- フェイルセーフ: AI API の失敗やレスポンスパース失敗は例外伝播ではなく警告ログを出してデフォルト値（0.0 やスキップ）で継続する箇所が多く、安全性を優先。
- テスト容易性: OpenAI 呼び出しや内部ヘルパーを分離しており、ユニットテストでのモック差し替えが可能。
- DuckDB 互換性: executemany に空リストを渡せない点など実運用での制約に配慮した実装を採用。
- 環境変数の自動ロードは便利だが、CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（score_news / score_regime を使用する際に必要）
- その他: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など

フィードバックやバグ報告、機能提案は Issue を立ててください。