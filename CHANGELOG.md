# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトは従来のセマンティックバージョニングに従います。  

※本ログは提供されたソースコードから推測して作成しています。

## [0.1.0] - 2026-04-01

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - パッケージ公開 API に data, strategy, execution, monitoring を定義。

- 環境設定 / config モジュール
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出は `__file__` を起点に `.git` または `pyproject.toml` を探索して行う（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサー実装（コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理等に対応）。
  - 環境変数保護（既存 OS 環境変数を protected として上書き回避）を実装。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能に：
    - J-Quants / KabuStation / Slack / DB パス（DuckDB / SQLite）/監視閾値（CPU/MEM/DISK）/実行環境（development/paper_trading/live）/ログレベル等。
    - 必須変数未設定時は明確な ValueError を送出。
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）を設定。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を用いて銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントスコアを生成。
    - チャンク処理（最大 20 銘柄/コール）、記事トリム（件数・文字数制限）、レスポンスバリデーション、スコアクリッピング（±1.0）を実装。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフを実装。非再試行のエラーはスキップして処理継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等に（対象コードのみ DELETE → INSERT）行い、部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し関数（内部 _call_openai_api）をモック可能に設計。
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し `market_regime` テーブルへ記録。
    - マクロニュースはマクロキーワードでフィルタし、最大記事数制限、OpenAI 呼び出し、リトライ、JSON パース検証を行う。
    - API 失敗時のフォールバック（macro_sentiment=0.0）や計算時のクリッピング、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT により冪等性を確保。
    - ルックアヘッドバイアス対策（datetime.today()/date.today()を直接参照しない、SQL の date < target_date 等で過去データのみ使用）。
    - OpenAI クライアント呼び出しは内部で分離し、news_nlp と結合しない設計。

- データモジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダーの管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB の market_calendar を利用し、データがない場合は曜日ベースでフォールバック（週末除外）する一貫した挙動。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants から差分取得 → 保存、バックフィル、健全性チェックを含む）。
  - pipeline / ETLResult
    - ETL パイプライン向けの結果データクラス `ETLResult` を定義（取得/保存件数、品質チェック結果、エラー一覧などを保持）。
    - ETL の設計指針を反映（差分更新、バックフィル、品質チェック続行方針、テスト用の id_token 注入等）。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装。
    - DuckDB 上で SQL を用いて高速に計算し、結果を (date, code) ベースの辞書リストで返却。
    - データ不足時は None を返す堅牢な設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）を実装。複数ホライズンを単一クエリで取得し、入力検証（horizons の範囲）を行う。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を実装。データ不足や同順位等の取り扱いに配慮。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数経由で取得し、Settings による必須チェックを導入。自動 .env ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 実装上の重要ポイント（運用上の注意）
- OpenAI 関連
  - 使用モデル: gpt-4o-mini（JSON Mode を利用）。API レスポンスのパースが失敗した場合は安全に 0.0 を返し処理を継続する設計。
  - 大量の API 呼び出しを行うため、課金・レート制限・レスポンス遅延に注意。エラー時は一部スコアが欠落する可能性があるが、DB の既存データを破壊しないよう配慮している。
  - テストでは内部の _call_openai_api をモック可能。ユニットテスト作成が容易。

- 環境設定
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を未設定で実行すると ValueError が発生するため、デプロイ前に環境の準備が必要。
  - デフォルトの DB パスや PID ファイルパスが設定されているため、実行環境のファイル権限やディレクトリ作成を確認すること。

- DuckDB / SQL 実装
  - 一部の DuckDB バージョンの制約（executemany に空リスト不可、リスト型バインドの不安定さ等）に配慮した実装になっている。運用時は DuckDB の互換性に注意。

- ルックアヘッドバイアス対策
  - すべての時系列/ETL/研究ロジックは内部で date 引数を受け取り、datetime.today()/date.today() 参照を避ける設計になっている。再現性のあるバッチ処理・バックテストが可能。

---

将来的なリリースでは、より詳細な互換性情報、既知の問題、マイグレーションガイドを追加予定です。