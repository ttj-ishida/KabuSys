# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買プラットフォームの基礎となる以下の機能群を実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開 API として data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を検出して .env → .env.local の順で読み込み（.env.local は上書き）。
  - 自動ロード抑止環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - .env パーサを実装（コメント、export プレフィックス、クォート内エスケープ、行内コメントの取り扱いに対応）。
  - 必須設定取得用の `_require` ヘルパーと多くのプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視設定: PID_FILE_PATH / CPU/MEM/DISK 閾値（デフォルト値あり）
    - 環境: KABUSYS_ENV（development, paper_trading, live のバリデーション）
    - ログレベル: LOG_LEVEL のバリデーション

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - バッチ処理: 最大 20 銘柄/チャンク、1銘柄あたり最大 10 記事・3000 文字でトリム。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数設定）。
    - レスポンスの厳密バリデーション（JSON 抽出・results 配列・code/score の検証、未知コードは無視、スコアは ±1.0 にクリップ）。
    - 書き込み: スコア取得済みコードのみを DELETE → INSERT して ai_scores を冪等更新（部分失敗時に既存データを保護）。
    - ニュースウィンドウ計算（JST ベース）: 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して DB 比較に使用。calc_news_window を提供。
    - 実装方針により datetime.today()/date.today() を直接参照せずルックアヘッドバイアスを防止。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは predefined マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）に JSON でセンチメント評価を行う。
    - LLM 呼び出しはリトライ・バックオフを実装し、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成のクリップ処理、閾値（BULL/BEAR）適用、market_regime テーブルへの冪等的書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー解決は api_key 引数または環境変数 OPENAI_API_KEY を利用し、未設定時は ValueError を送出。

- データモジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB 登録がない日については曜日ベースでフォールバック（土日非営業）。
    - 次/前営業日の探索は最大検索日数制限を設け ValueError で明示的に失敗を返す。
    - 夜間バッチ calendar_update_job を実装。J-Quants API から差分取得し冪等保存、バックフィル・健全性チェックを行う。
    - jquants_client（外部クライアント）と連携する前提。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を定義し ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - ETL の設計方針・定数・ユーティリティ（テーブル存在チェック・最大日付取得など）を実装。data.etl から ETLResult を再エクスポート。
    - 差分更新・バックフィル・品質チェックのための基盤が整備されている（jquants_client / quality モジュールと連携する想定）。
    - 注意: pipeline モジュールの一部はファイル末尾で切れているが、ETLResult と主要ユーティリティは実装済み。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（営業日ベースのラグを使用）。
    - ボラティリティ / 流動性: 20日 ATR（true range を適切に扱う実装）、atr_pct、20日平均売買代金、出来高比率を算出。
    - バリュー: raw_financials から最新の財務データ（report_date <= target_date）を取得し PER、ROE を算出（EPS が 0/NULL の場合は None）。
    - DuckDB 上の SQL + ウィンドウ関数を用いた効率的実装。データ不足時は None を返す方針。

  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）を実装（LEAD を用いた1クエリ取得、horizons の検証）。
    - IC（情報係数） calc_ic: factor_records と forward_records を code で結合し、Spearman（ランク相関）を計算（ties は平均ランク）。
    - rank ユーティリティ（同順位の平均ランクを返す、浮動小数の丸め対策あり）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する集計ユーティリティ。
    - 実装は標準ライブラリと DuckDB のみで依存を最小化。

### Security
- 環境変数による API キー管理を前提。OpenAI キーは api_key 引数で注入可能（テスト容易性と明示的なキー管理を想定）。

### Design / Implementation notes
- ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない方針を採用（すべての主要関数が target_date 引数を取る）。
- OpenAI 呼び出しは各モジュールで独立した内部関数として実装（モジュール間でのプライベート関数共有を避ける）。
- API 呼び出し失敗時は例外で即停止させるのではなく、フェイルセーフ（0.0 やスキップ）して継続する箇所を多数設け、安全性優先とした。
- DuckDB をデータ処理の中心に据え、冪等的な DB 書き込み（DELETE → INSERT、ON CONFLICT 形式を利用想定）を基本戦略とする。

### Removed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

---

参考: 主に以下ファイル群を実装済み
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/__init__.py
- src/kabusys/data/calendar_management.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/etl.py
- src/kabusys/data/__init__.py

今後の予定（例）
- pipeline の ETL 実行フローの完成、jquants_client / quality モジュールとの統合テスト
- strategy / execution / monitoring の詳細実装とエンドツーエンドテスト
- ドキュメント、例示スクリプト、CI ワークフローの追加

（以上）