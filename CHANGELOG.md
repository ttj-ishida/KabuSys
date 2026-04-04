# Changelog

すべての重要な変更を記録します。形式は「Keep a Changelog」に準拠します。  
このファイルはバージョン履歴の要約をコードベース（src/ 以下）から推測して作成しています。

なお、バージョン番号はパッケージメタデータ（kabusys.__version__）に準拠しています。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0, __all__ 指定）。
- 設定管理
  - 環境変数/設定管理モジュールを追加（kabusys.config）。
    - .env 自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パース機能を強化（export 形式、クォート付き値、インラインコメントの扱い等）。
    - 必須環境変数検査用の _require() と Settings クラスを提供。
    - 主要な設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, OPENAI 用キー参照、LINE 関連、データベースパス、監視関連パス・閾値、KABUSYS_ENV/LOG_LEVEL 等）。
    - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）やデフォルト値を設定。
- AI / NLP
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を収集し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数のトリム、レスポンス検証、スコアクリップを組み込み。
    - API リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフに対応。部分失敗時は他銘柄スコアを保護するために書き込み対象を限定して DELETE→INSERT を実行。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
    - calc_news_window() により JST ベースのニュース収集ウィンドウ計算を提供。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しに対する堅牢なリトライ処理とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア計算ロジック、しきい値、ロギングを実装。
    - news_nlp とは別実装の OpenAI 呼び出し関数を用意し、モジュール結合を避ける設計。
- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェックを行う設計に基づくユーティリティ枠組みを実装（J-Quants クライアント連携を想定）。
    - 品質チェックの検出結果を収集し、ETL 結果へ格納する仕組み。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API 経由で差分取得・バックフィル・保存（冪等）を行う。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 登録あり→DB 優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 最大探索日数、健全性チェック、バックフィル日数などの保護ロジックを実装。
- リサーチ / ファクター（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）などのファクター計算を実装。DuckDB を用いた SQL ベースの実装。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman / ランク相関）計算、ファクター統計サマリー、ランク計算ユーティリティを実装。外部依存（pandas 等）なしで実装。
  - research パッケージのエクスポート整理（主要関数を __all__ に追加）。
- 監視・実行関係（設定項目）
  - PID ファイル・キルフラグ・リソース閾値（CPU/MEM/DISK）を Settings で提供。監視プロセスに必要な設定を集約。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動ロードでは OS 環境変数を保護（.env の上書き防止）する実装を導入。必要な場合は .env.local による上書きが可能。
- OpenAI API キーはデフォルトで環境変数 OPENAI_API_KEY を参照。必要に応じて各 API 呼び出しに api_key を直接渡して使用可能。

### 注意事項 / 実装上の設計上のポイント (Notes)
- ルックアヘッドバイアス対策
  - AI モジュールおよびリサーチ関数はいずれも内部で datetime.today() / date.today() を参照しない設計。外部から target_date を与えて処理することにより、将来データ参照（ルックアヘッド）を防止。
  - DB クエリは date < target_date や半開区間などで未来データ参照を防ぐように注意を払っている。
- OpenAI 呼び出しの堅牢化
  - gpt-4o-mini を使用し、JSON モード応答を想定。リトライや 5xx 判定、レスポンスパース失敗時のフォールバック（例: macro_sentiment=0.0、スキップ）を実装。
  - テスト時には内部の _call_openai_api を unittest.mock.patch により差し替え可能。
- DB 書き込みの冪等性
  - market_regime や ai_scores 等への書き込みは DELETE→INSERT あるいは ON CONFLICT 相当の冪等処理を行い、部分失敗時にも既存データを不必要に削除しない工夫をしている。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、ROLLBACK 失敗時には警告ログを出力する。
- DuckDB 互換性
  - executemany に空リストを渡せない等の既知制約を考慮した実装（書き込み前の空チェック）。
- Calendar フォールバック
  - market_calendar が存在しない場合は曜日（平日/土日）ベースでフォールバックするため、DB 未取得時も動作する。
- エラー耐性
  - 各種 API 失敗やパースエラーは基本的に「失敗を他処理に伝播させずフォールバックして継続」する設計（ログ出力は行う）。ETLResult により品質問題やエラーを呼び出し元に返す構成。

### 想定される必須 / 重要な環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabu API 用）
  - OPENAI_API_KEY（AI モジュール実行時に必要。api_key 引数で代替可）
- 任意 / デフォルトあり:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV（development, paper_trading, live のいずれか）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

### 互換性 / 破壊的変更 (Breaking Changes)
- 初回リリースのため破壊的変更はありません。

### マイグレーション / アップグレードノート
- なし（初回リリース）

---

開発・運用時の補足:
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化するとテスト環境での環境変数制御が容易です。
- OpenAI 呼び出し部分はモック差し替えの想定がされているため、ユニットテストでの外部 API 依存を切り離しやすくなっています。
- ETL, calendar_update_job, AI スコアリングなどは外部 API（J-Quants / OpenAI）に依存するため、実運用では各 API キーやネットワーク接続、API レート制限への配慮が必要です。