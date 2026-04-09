CHANGELOG
=========

すべての重要な変更履歴はここに記録します。本プロジェクトは Keep a Changelog の形式に準拠します。

該当リポジトリのコードベースから推測して記載しています。実装上の設計方針やフェイルセーフ挙動、互換性配慮なども併記しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 基本パッケージ初期リリース
  - パッケージトップ: kabusys/__init__.py にてバージョン "0.1.0" として公開、主要サブパッケージを __all__ でエクスポート。
- 環境設定 / 設定読み込みモジュール（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（プロジェクトルート検出は .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートを考慮したエスケープ処理
    - コメントの扱い（クォート外での # を適切に無視）
  - protected キー（既存 OS 環境変数）を保持するオプションによる上書き制御。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / paper trading / 監視設定 / システム設定 等のプロパティを公開。
  - 必須環境変数取得用の _require 関数（未設定時は ValueError を送出）。
  - 各種検証:
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄単位のニュースを作成
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチスコアリングを実装（バッチサイズ最大 20 銘柄）
    - リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）を実装
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score の型検査、既知コードのみ採用、スコアの ±1.0 クリップ）
    - DuckDB 互換性を考慮した idempotent 書き込み（DELETE → INSERT、executemany 空リスト回避）
    - calc_news_window を公開し、JST ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime に変換
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）
    - 設計として「datetime.today()/date.today() を直接参照しない」ことでルックアヘッドバイアスを回避
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime 判定（bull/neutral/bear）
    - MA200 計算は target_date 未満のデータのみを使用しルックアヘッドを防止
    - マクロニュース抽出はキーワードマッチ（デフォルトリストあり）で行い、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 を使用
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）
    - API リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルによる祝日・半日取引・SQ 日の管理と、DB が無い場合の曜日ベースのフォールバック実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日ユーティリティを提供
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）
    - 最大探索日数やバックフィル日数等の安全ガードを実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL 処理の設計に基づく差分取得 / 保存 / 品質チェックフレームワークの骨格
    - ETLResult dataclass を定義（取得数、保存数、品質問題・エラー列挙、has_errors / has_quality_errors / to_dict を提供）
  - ETLResult を kabusys.data.etl 経由で再エクスポート
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離）
    - Volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio
    - Value: PER（EPS が 0 または欠損の場合は None）、ROE（raw_financials から最新データを取得）
    - DuckDB 上で SQL + Python による高性能実装、データ不足時の None ハンドリング
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（デフォルト horizons=[1,5,21]）を一回のクエリで取得する実装
    - calc_ic: スピアマン順位相関による IC 計算（必要なレコード数チェック、None ハンドリング）
    - rank: 同順位は平均ランク化するランク関数（丸めによる ties 対策）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - いくつかのユーティリティをパッケージレベルで再エクスポート（zscore_normalize 等）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取得に関しては api_key 引数または環境変数 OPENAI_API_KEY を使用する仕様を明記。必須未設定時は明確に ValueError を送出して失敗させることで、キー漏洩等の曖昧さを防止。

Notes / Implementation decisions
- ルックアヘッドバイアス回避:
  - AI モジュール（news_nlp/regime_detector）および research モジュールは内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計。
- フォールバック / フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを 0.0 にフォールバックして処理継続（例外を上げずにログ出力）。
  - DB 書き込みはトランザクションで保護（失敗時は ROLLBACK を試行し、失敗理由を上位へ伝播）。
- DuckDB 互換性:
  - executemany に対する空リスト回避やリスト型バインドの回避など、DuckDB のバージョン差異を考慮した実装上の工夫を行っている。
- テスト容易性:
  - OpenAI 呼び出しを _call_openai_api 関数でラップし、unittest.mock.patch による差し替えを想定した設計。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートが存在する場合は、それを優先してください。