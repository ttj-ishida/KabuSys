# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初期公開リリースに関する要約は以下の通りです。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージ初期公開
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いを考慮。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - override / protected（OS 環境変数保護）オプションを持つ .env 読み込み。
  - Settings クラスを提供し、アプリ設定（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境・ログレベル判定等）を型付きプロパティで取得。
  - 必須環境変数未設定時に明確なエラーメッセージを返す _require() を実装。

- ニュース NLP（AI） (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC ベースで変換）算出機能を実装（calc_news_window）。
  - チャンク処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数と文字数の上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
  - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx）、指数バックオフ、最大リトライ制御を実装。
  - レスポンスバリデーション: JSONパース、results 配列、code/score の存在チェック、未知コードの無視、スコアの有限性チェック、±1.0 でクリップ。
  - DuckDB への冪等的書き込み（該当コードのみ DELETE → INSERT）を実装。部分失敗時に既存スコアを保護。
  - テスト用フック: _call_openai_api を patch して差し替え可能。

- 市場レジーム判定（AI + 指数） (src/kabusys/ai/regime_detector.py)
  - ETF 1321（225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
  - MA200 比率計算、マクロキーワードで raw_news を抽出、OpenAI 呼び出し（独立実装）による macro_sentiment 評価、合成スコアのクリップとラベリングを実装。
  - API 失敗時のフェイルセーフ（macro_sentiment=0.0）、冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT, ROLLBACK 処理）を実装。
  - テスト用途の差し替えポイントを設け、ルックアヘッドバイアス防止の設計を採用。

- データ / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar を扱うユーティリティ群を実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - market_calendar が存在しない場合の曜日ベースフォールバック（平日を営業日）に対応。
  - _MAX_SEARCH_DAYS による探索上限、安全性チェック、DB データ優先の振る舞い等を実装。
  - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に保存（バックフィル・健全性チェック含む）。
  - jquants_client との連携を想定（fetch/save 呼び出し）。

- ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約・辞書変換可能に。
  - 差分取得、backfill のデフォルト実装方針（最終取得日の数日前から再取得）、品質チェックの取扱い方針（重大度を判定して呼び出し元に通知）を想定した設計。
  - データパイプラインの公開型（ETLResult）を etl モジュールで再エクスポート。

- 研究用モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB 上の SQL で算出。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比 を算出。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（EPS 0/欠損時は None）。
    - SQL ウィンドウ関数を活用した高性能な集計を採用、データ不足時は None を返す。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）に対する将来リターンを LEAD を使って一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（record マージ、3 件未満で None）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計要約（count, mean, std, min, max, median）を実装。
  - data.stats の zscore_normalize を再利用できるよう __init__ で再エクスポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 注意 / 補足 (Notes)
- ルックアヘッドバイアス防止:
  - 全ての AI / ETL / 研究モジュールは内部で datetime.today() / date.today() を直接参照しない設計。target_date 引数ベースで動作するため、将来データ参照（ルックアヘッド）を防止しています。
- OpenAI API:
  - 使用モデルは gpt-4o-mini。JSON Mode を用いた厳密な JSON 出力を期待するが、パース耐性（前後テキストの除去など）を備えています。
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を発生させます。
  - テスト用に _call_openai_api を差し替えることができるフックが用意されています。
- フェイルセーフ & ロギング:
  - API 失敗時は例外を無闇に投げずフェイルセーフなデフォルト（例: macro_sentiment=0.0、該当チャンクはスキップ）で継続する設計。重要な失敗はログに記録。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護され、ROLLBACK 失敗時はログ出力。
- DuckDB の実装上の注意:
  - DuckDB 0.10 の executemany は空リストを受け付けない制約を考慮した実装（空チェックを行ってから executemany を呼ぶ）。
  - 日付値は明示的に date オブジェクトへ変換するユーティリティを提供。
- 環境変数の自動ロード:
  - プロジェクトルートが見つからない場合は自動ロードをスキップします。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動ロードを抑止できます。
- デフォルトパス:
  - DuckDB/SQLite/監視 PID/フラグファイルのデフォルトパスは settings で指定（例: data/kabusys.duckdb など）。必要に応じて環境変数で上書き可能。

### セキュリティ (Security)
- 秘密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 等）は環境変数で管理することを前提としています。Settings クラスは必須項目未設定時に明示的にエラーを出します。
- .env 読み込みは OS 環境変数を protected として上書きから守る仕組みを備えています。

---

今後の予定（例）
- strategy / execution / monitoring の実装拡充（本リリースでは基盤と研究・データ・AI 部分を提供）。
- ユニットテスト拡充、OpenAI 呼び出しの抽象化やモックの標準化、J-Quants クライアントの安定化。

（初期リリース）