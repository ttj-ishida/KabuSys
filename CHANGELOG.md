# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
初版リリースの内容はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-09

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買・リサーチ用ライブラリ。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数を自動読み込み（優先順位: OS env > .env.local > .env）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - プロジェクトルート判定は __file__ 起点で親ディレクトリに `.git` または `pyproject.toml` を探索。
  - .env パーサー:
    - コメント行と空行を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなし値のインラインコメント解析（`#` が直前に空白/タブであればコメント扱い）。
  - 設定オブジェクト `Settings` を公開 (`settings`)。以下の項目を環境変数から取得し、妥当性チェックを実施:
    - J-Quants / kabuステーション / LINE API の設定（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `LINE_CHANNEL_ACCESS_TOKEN` 等）。
    - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）とファイルパス系（PID, kill flag）。
    - Paper Trading の `PAPER_FILL_MODE`（"instant" | "partial" | "never" | "reject"）の検証。
    - 環境 `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の検証。
    - 監視閾値（CPU/MEM/DISK）や kill フラグの初期挙動フラグ等。

- AI モジュール (kabusys.ai)
  - news_nlp (kabusys.ai.news_nlp)
    - raw_news / news_symbols を基に銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) の JSON Mode を使ってセンチメントを算出。
    - 処理フロー:
      - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST を UTC で変換して対象抽出（calc_news_window）。
      - 1銘柄あたり最新記事を最大 _MAX_ARTICLES_PER_STOCK 件、文字数は _MAX_CHARS_PER_STOCK でトリム。
      - バッチ処理: 1回の API 呼び出しで最大 _BATCH_SIZE (=20) 銘柄を送信。
      - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンス検証: JSON パース、"results" リスト、各要素の code/score を検証。スコアは ±1.0 にクリップ。
      - DuckDB への冪等書き込み: 成功したコードのみ DELETE → INSERT の形で置換（部分失敗時に他コードを保護）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で抽象化し patch 可能。

  - regime_detector (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定。
    - 処理フロー:
      - 1321 の ma200_ratio を DuckDB から計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
      - calc_news_window を使ってマクロ関連記事タイトルを抽出（キーワードでフィルタ）。
      - OpenAI (gpt-4o-mini) により macro_sentiment を取得（記事がない場合は API コールを省略し 0.0 を使用）。
      - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - DuckDB の market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - フェイルセーフ:
      - API 失敗やパース失敗時は macro_sentiment を 0.0 にフォールバックし例外を上げない（ログ出力のみ）。
      - API キー解決は引数優先、なければ環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム、バリュー、ボラティリティ（流動性含む）ファクター計算を提供。
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev（データ不足時は None）。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時は None）。
    - calc_value(conn, target_date): per（EPS が 0/欠損なら None）と roe（raw_financials からの最新値）。
    - 全て DuckDB の prices_daily / raw_financials を使用し、外部 API へはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 翌日/翌週/翌月などの将来リターンを計算（horizons 検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank(values): 同順位は平均ランクを返すランク変換（round で数値丸めして ties を安定処理）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計要約。
  - 便利関数 zscore_normalize は kabusys.data.stats から再エクスポート。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダーを扱うユーティリティ群:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - 特徴:
      - market_calendar テーブルが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
      - DB 登録があれば DB 値を優先、未登録日は曜日ベースで一貫して補完。
      - _MAX_SEARCH_DAYS による探索上限で無限ループを防止。
    - calendar_update_job(conn, lookahead_days): J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェック有）。
    - jquants_client (kabusys.data.jquants_client) を参照してデータ取得/保存を行う（クライアント実装はコード内参照）。
  - pipeline (ETL)
    - ETLResult データクラスを提供（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得・保存件数、品質チェック結果（quality.QualityIssue のリスト）、エラー概要を保持し、has_errors / has_quality_errors プロパティを提供。
    - ETL パイプライン設計方針:
      - 差分取得、冪等保存（ON CONFLICT DO UPDATE 想定）、品質チェックは致命的エラーがあっても収集継続する設計。
      - バックフィルや最小データ日付（_MIN_DATA_DATE）等のパラメータを持つ。

- テスト・堅牢性向け設計
  - OpenAI 呼び出しは各モジュールで _call_openai_api 関数を独自に持ち、テスト時に patch して差し替え可能。
  - ルックアヘッドバイアス防止のため、内部実装は date.today() / datetime.today() を直接参照しない設計（target_date を明示的に受ける）。

### Changed
- 初版のため該当なし（新規追加のみ）。

### Fixed
- 初版のため該当なし。

### Notes / 実装に関する補足
- OpenAI の使用
  - 使用モデル: gpt-4o-mini（news_nlp, regime_detector）。
  - JSON Mode を利用し厳密な JSON 出力を期待するが、パースの堅牢化（前後の不要テキスト除去等）を行っている。
  - レート制限や 5xx 等に対しては最大リトライ回数・指数バックオフを実装。致命的な失敗時はフェイルセーフとして 0.0 や空スコアを使用して継続する。
- DuckDB に関する互換性考慮
  - executemany に空リストが渡せないバージョン（DuckDB 0.10 等）への対応がある（空時は実行をスキップ）。
  - 日付型の取り扱いを一貫して行うユーティリティ（_to_date）を提供。
- DB 書き込みは冪等性を重視（DELETE → INSERT のパターン等）し、失敗時はトランザクションをROLLBACKして上位へ例外を伝播させる。
- 外部クライアント（jquants_client, quality 等）はモジュール分離され、ETL やカレンダ更新はそれらを利用する構成。

---

（上記は提供されたコードファイル群からの推測に基づく CHANGELOG です。実際の変更履歴やリリースノートは開発履歴・コミットログに基づいて適宜調整してください。）