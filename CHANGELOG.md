# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

初期リリース — "KabuSys" 日本株自動売買システムの最初の公開バージョン。

### 追加 (Added)
- パッケージ構成
  - パッケージ名: kabusys
  - public API: kabusys.__all__ に ["data", "strategy", "execution", "monitoring"] を公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ローダ実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォートあり/なしでの差別化）
  - .env 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定時のみ）
  - protected set による OS 環境変数保護（上書き禁止）
  - Settings クラスを提供し、環境変数をプロパティとして扱う:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（_require による未設定時の明示的エラー）
    - KABU_API_BASE_URL のデフォルト値 (http://localhost:18080/kabusapi)
    - LINE 関連設定（任意）
    - データベースパスのデフォルト: DUCKDB_PATH, SQLITE_PATH
    - Paper Trading 関連:
      - PAPER_FILL_MODE をサポート（instant | partial | never | reject）と検証
      - PAPER_TRADING_SQLITE_PATH による Paper 用 SQLite パス上書き
    - 監視設定: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK の閾値
    - システム設定: KABUSYS_ENV（development|paper_trading|live）検証、LOG_LEVEL 検証
    - ヘルパープロパティ: is_live, is_paper, is_dev

- AI/NLP モジュール (src/kabusys/ai/)
  - ニュースセンチメント (news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini, JSON mode) による銘柄単位センチメントを ai_scores テーブルへ書き込み
    - タイムウィンドウ計算: calc_news_window（JSTベース: 前日15:00～当日08:30 を UTC に変換）
    - バッチ処理: 1回の API コールで最大 _BATCH_SIZE（20）銘柄
    - 入力トリム: 1銘柄あたり最大 _MAX_ARTICLES_PER_STOCK（10 件）、最大文字数 _MAX_CHARS_PER_STOCK（3000）
    - エラー処理: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。その他はスキップしフェイルセーフで継続
    - レスポンス検証: JSON 抽出・results リストと個々の {code, score} 検証、スコアを ±1.0 にクリップ
    - DB 書き込みは部分失敗時に既存スコアを保護する（DELETE → INSERT の明示的置換、対象 code を限定）
    - テスト容易性: _call_openai_api を patch して差し替え可能
  - 市場レジーム判定 (regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321（Nikkei225連動ETF）の 200日移動平均乖離（重み70%）と LLM によるマクロセンチメント（重み30%）を合成して market_regime テーブルへ冪等書き込み
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）
    - マクロニュース抽出は calc_news_window を使用し、マクロキーワードリストでフィルタ
    - OpenAI 呼び出しはリトライ/バックオフを実装、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - 出力ラベル: "bull" / "neutral" / "bear"（閾値で判定）
    - テスト容易性: _call_openai_api を差し替え可能

- Research モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev を計算（200日未満は None）
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足は None）
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER（EPS=0/欠損→None）と ROE を計算
    - 実装は DuckDB の SQL ウィンドウ関数を活用し、date/code 単位で辞書リストを返す
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を一括 SQL で取得
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算（有効レコード < 3 の場合 None）
    - rank(values): 同順位は平均ランクに処理（round(v, 12) による安定化）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
  - 研究系ユーティリティは外部依存を極力排し、DuckDB と標準ライブラリのみで動作

- Data プラットフォーム (src/kabusys/data/)
  - calendar_management.py:
    - 市場カレンダー操作関数を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar テーブルがない場合は曜日ベースでフォールバック（週末は非営業日）
    - next/prev/get_trading_days は DB 登録有無にかかわらず一貫した動作を保証する設計（未登録日は曜日フォールバック）
    - calendar_update_job(conn, lookahead_days): J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新、バックフィル・健全性チェックを実装
  - pipeline.py / etl.py:
    - ETLResult dataclass を導入（取得件数・保存件数・品質問題・エラーの集約）
    - ETLResult.to_dict() により品質問題を dict へ変換してログ等に利用可能
    - ETL の設計方針: 差分更新、バックフィル、品質チェックを行い、部分失敗時も他データを保護する（Fail-Fast しない）
    - data.etl で ETLResult を再エクスポート

- 汎用 / 設計上の注意点
  - ルックアヘッドバイアス防止: 各処理で datetime.today()/date.today() を直接参照せず、target_date パラメータ駆動で動作
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避など）
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の利用）
  - ロギングを各モジュールに導入し、失敗時は警告/例外ログで問題を通知
  - テスト容易性: OpenAI 呼び出し等外部依存点は差し替え可能に実装

### 変更 (Changed)
- 初期リリースのため、過去バージョンからの変更履歴はありません。

### 修正 (Fixed)
- 初期リリースのため、既知の「修正」はありません。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 環境変数による機密情報（JQUANTS_REFRESH_TOKEN 等）は必須プロパティとして明示し、未設定時はエラーを返すことで誤動作を防止。

注記:
- 本リリースは機能の第一実装を収めています。運用や追加機能（戦略実装、発注エンジン、監視 UI 等）は今後のリリースで提供する予定です。