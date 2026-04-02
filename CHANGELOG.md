# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

注: コードベースから推測して記載しています。実装上の設計意図や注意点も併記しています。

## [0.1.0] - 2026-04-02

### Added
- パッケージ初回リリース (kabusys v0.1.0)
  - パッケージメタデータ: src/kabusys/__init__.py にて __version__ を "0.1.0" として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数からの自動読み込み機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .git または pyproject.toml を起点にプロジェクトルートを探索するロジックを追加（CWD 非依存）。
  - .env 行パーサーを実装:
    - export KEY=val 形式対応
    - シングル・ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの場合のインラインコメント認識（直前が空白/タブの場合のみ）
  - .env 読み込み時の保護機構: OS 既存環境変数は protected set により上書きを防止可能。
  - Settings クラスを提供し、各種必須設定と既定値をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
    - DB パス (DUCKDB_PATH/SQLITE_PATH)、監視設定 (PID_FILE_PATH, CPU/MEM/DISK 閾値) の既定値
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）
    - is_live / is_paper / is_dev のヘルパープロパティ

- ニュース NLP（AI）モジュール (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI (gpt-4o-mini) に JSON モードでバッチ送信してセンチメントを算出。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC変換済み）を対象にスコアリング。
  - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・最大 3000 文字でトリム。
  - 再試行・指数バックオフ対応（429/ネットワーク/タイムアウト/5xx）。
  - レスポンスの厳格なバリデーション実装（JSON 抽出、results 配列、code/score チェック、数値化、±1.0 クリップ）。
  - DuckDB 互換性を考慮した書き込み（ai_scores テーブル）実装。部分成功時は該当コードのみ削除→挿入して既存データを保護。
  - テスト用フック: _call_openai_api を patch 可能（unittest.mock で差し替えやすい）。

- 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - マクロニュース抽出はキーワードベース（日本・米国を含む）で最大 20 件取得。
  - OpenAI 呼び出しは gpt-4o-mini を利用、JSON 出力パース、リトライ/バックオフ、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - 判定結果は market_regime テーブルに冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込む。
  - ルックアヘッドバイアス防止の設計: datetime.today() 等を参照せず、prices_daily クエリも target_date 未満（排他）で取得。

- リサーチ / ファクター計算モジュール (src/kabusys/research/)
  - factor_research.py:
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）計算。
    - Volatility: 20日 ATR（atr_20）、相対ATR (atr_pct)、20日平均売買代金、出来高比率。
    - Value: PER（price / EPS）、ROE（raw_financials から最新レコードを参照）。
    - DuckDB を用いた SQL ベース実装、欠損時は None を返す挙動。
  - feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns) — 任意ホライズンに対応（既定 [1,5,21]）、ホライズンは検証済み（1〜252）。
    - IC（Information Coefficient）計算: Spearman のランク相関（rank 関数で同順位は平均ランク処理）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None を除外）。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）。

- データプラットフォーム関連 (src/kabusys/data/)
  - calendar_management.py:
    - market_calendar を用いた営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB にデータがない場合は曜日ベース（週末は非営業日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを実装）。
  - pipeline.py / etl.py:
    - ETLResult dataclass を導入して ETL 実行結果を集約（取得件数、保存件数、品質チェック結果、エラー集約）。
    - ETL の差分更新方針、backfill、品質チェック（quality モジュール連携）を意図した設計。
    - etl.py では pipeline.ETLResult を再エクスポート。

### Changed
- 多くのモジュールで「ルックアヘッドバイアス防止」を明示的に設計方針に採用（datetime.today() / date.today() を直接参照しない）。
- OpenAI 呼び出しで JSON mode を想定し、レスポンスの厳格なパースとフォールバックを導入。
- DuckDB 固有の挙動（executemany の空リスト制約、リスト型バインドの不安定さ）を考慮した実装。

### Fixed / Robustness
- API 呼び出し周りの耐障害性強化:
  - RateLimit, 接続エラー, タイムアウト, サーバ 5xx をリトライ対象にし指数バックオフを実装。
  - 非 5xx の APIError やレスポンスパースエラーは警告ログを出し安全にフォールバック（例: macro_sentiment=0.0、該当チャンクスキップ）。
- .env パーサーでのクォート内エスケープ、インラインコメント処理等を精緻化。
- DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 相当の保険）。

### Known issues / TODO
- src/kabusys/data/pipeline.py の末尾に実装途中と見られる箇所があり、タイポまたは未完のコードが残っています（`return date.fro` のような不完全な行）。このため pipeline._get_max_date の戻り値処理が壊れている可能性があります。修正・ユニットテスト追加が必要です。
- monitoring モジュールは __all__ に含まれているが、今回のスナップショット内に実装ファイルが見当たりません（将来的に追加予定）。
- OpenAI 連携部分は API キーの取り扱い（環境変数 OPENAI_API_KEY）に依存するため、デプロイ時のシークレット管理に注意が必要。

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入し、既存の機密情報が .env によって上書きされるリスクを低減。
- OpenAI API キー未設定時は ValueError を発生させて明示的に失敗させる設計。

---

将来的なリリースでは以下を検討してください:
- pipeline モジュールの未完成箇所の修正とユニットテスト追加。
- monitoring モジュール（実装/公開 API）の追加。
- OpenAI 呼び出しのメトリクス収集（呼び出し数、レイテンシ、エラー率）やコスト制御。
- .env パーサーの追加ユースケース（複数行の値やより複雑なエスケープ）への対応。