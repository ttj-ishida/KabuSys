# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

※初回リリース（0.1.0）をコードベースから推測して作成しています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォームのコア機能群を提供します。主な追加点・設計方針は以下の通りです。

### Added
- 基本パッケージ公開
  - パッケージルート: `kabusys`（__version__ = 0.1.0）
  - 公開モジュール: data, strategy, execution, monitoring

- 環境設定 / .env 管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込み。
  - 自動読み込みの探索はパッケージファイル位置から親ディレクトリを辿り `.git` または `pyproject.toml` をプロジェクトルートとして特定（CWD 非依存）。
  - .env のパース機能を実装（コメント行・空行・`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理などを考慮）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`.env.local` は上書き（override）を許可。
  - OS 環境変数の保護（protected set）を実装し、override 時に既存の OS 環境値を守る。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意（テスト用途）。
  - Settings クラスを提供し、以下の設定へプロパティ経由でアクセス可能:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（必須）
    - データベース: DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - システム: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境値未設定時は明示的な ValueError を送出する必須取得ヘルパーを実装。

- AI 系機能（src/kabusys/ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり最新最大 10 記事、文字数トリム上限 3000）。
    - OpenAI（gpt-4o-mini、JSON Mode）へ最大 20 銘柄ずつバッチ送信（_BATCH_SIZE=20）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を想定した指数バックオフ（最大リトライ回数・待機時間を設定）。
    - レスポンスの堅牢なバリデーション（JSON パースの復元ロジック、"results" キーの検証、コードの正規化、数値チェック、スコア ±1 にクリップ）。
    - スコアは ai_scores テーブルへ冪等的に (DELETE → INSERT) 書き込む。部分失敗時に既存スコアを保護する設計。
    - API 失敗やレスポンス異常はその銘柄チャンクをスキップし、例外を全部バブルアップしないフェイルセーフ設計。
    - テスト容易性: OpenAI 呼び出しをモジュール内で分離（patch で差し替え可能）。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225 連動型）に対する 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を算出。
    - MA 算出は target_date 未満のデータのみ利用し、ルックアヘッドバイアスを防止。
    - マクロ記事は news_nlp.calc_news_window を用いてウィンドウ抽出し、キーワードフィルタで最大 20 記事を取得。
    - OpenAI 呼び出しは独立実装、失敗時は macro_sentiment=0.0 のフェイルセーフ。リトライ処理・5xx 判定を実装。
    - レジームスコアの合成とクリップ、閾値判定（BULL/BEAR）、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を提供。J-Quants クライアント経由で差分取得→保存（jq.fetch_market_calendar / jq.save_market_calendar 想定）。
    - 営業日の判定・ナビゲーション関数を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーが存在しない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - 最大探索日数やバックフィル日数、健全性チェック（将来日付が異常に遠い場合はスキップ）などを実装。
    - 全日付は date オブジェクトで扱い timezone 混入を回避。

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（target_date、取得/保存件数、quality_issues、errors、ヘルパー has_errors / has_quality_errors / to_dict）。
    - pipeline モジュールから ETLResult を再エクスポート（data.etl）。
    - ETL パイプラインの設計方針を実装（差分更新、backfill、品質チェックの集約、id_token 注入可能など）。

- 研究用ユーティリティ（src/kabusys/research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から最新の eps/roe を取り出し PER・ROE を算出（EPS=0/欠損は None）。
    - DuckDB SQL を主体に実装し、外部 API にはアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクにする実装（丸めにより ties 検出の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリ。

- 共通設計方針・実装上の注意点
  - いずれのスコア/計算関数も内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを防止。
  - DuckDB を主要なローカル分析 DB として利用（DuckDB のバージョン依存性に配慮した実装や executemany の空リスト対策を含む）。
  - OpenAI API 呼び出し周りはリトライやタイムアウト、レスポンスパースの堅牢性を重視。
  - ロギングを各モジュールで適切に行い、警告/情報ログで状態を明示。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （セキュリティ修正・注意点）
  - 環境変数の読み込みで OS 環境変数を上書かない仕組み（protected set）を導入し、意図しない環境上書きを防止。

---

注:
- 上記はコードベースの実装内容から推測してまとめた CHANGELOG です。実際のリリースノートには利用者向けの追加情報（インストール手順、依存関係のバージョン、既知の制限やマイグレーション手順など）を追記することを推奨します。