CHANGELOG
=========
すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の慣例に従っています。

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
------------------
初回リリース。以下の主要機能・実装を含みます。

Added
- パッケージ構成
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開サブパッケージ/モジュール: data, research, ai, config（トップレベル __all__ に登録）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォート無し時のインラインコメント扱いルールを実装。
  - 環境変数上書き制御（override / protected）を実装し、OS 環境変数の保護が可能。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等をプロパティで提供。
  - env/log_level に対する値検証を実装（許容値以外は ValueError）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - 市場カレンダーを扱うユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索上限（_MAX_SEARCH_DAYS）による安全制御。
    - calendar_update_job により J-Quants からの差分取得・バックフィル保存（lookahead / backfill / sanity check を実装）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL の取得件数、保存件数、品質問題、エラー等を集約）。
    - 差分取得・保存・品質チェックのためのユーティリティ（テーブル存在チェック、最大日付取得など）。
    - jquants_client / quality モジュールを前提とした差分ETL設計。

  - etl モジュールの公開インターフェース（ETLResult を再エクスポート）。

- 研究（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン, ma200_dev）、ボラティリティ（20日 ATR, atr_pct）、バリュー（PER, ROE）等のファクター計算関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの高効率実装。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応、入力検証）。
    - IC（スピアマン ρ）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）。
    - 外部ライブラリに依存しない純標準ライブラリ実装。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を使い、銘柄毎にニュースを集約して OpenAI（gpt-4o-mini / JSON mode）でセンチメント評価し ai_scores に保存する score_news 実装。
    - ニュースウィンドウ計算（JST ベース）を calc_news_window として提供（JST→UTC の naive datetime を返す）。
    - バッチ送信（最大 20 銘柄/chunk）、記事トリム（最大記事数 / 最大文字数）、レスポンスの厳密検証とスコアクリッピング（±1.0）。
    - API エラーや 5xx / 429 / タイムアウトへの指数バックオフ・リトライ、失敗時は対象銘柄をスキップして処理継続（フェイルセーフ）。
    - OpenAI レスポンスの JSON パースに冗長な前後テキストが混ざる場合の復元ロジックを実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - DuckDB の executemany に対する互換性考慮（空リストを渡さないガード）。

  - regime_detector:
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime に書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロキーワードで raw_news を抽出し、LLM で macro_sentiment を評価（記事がない場合は LLM 呼び出しをスキップ、0.0 を採用）。
    - OpenAI 呼び出しは news_nlp と独立した実装でモジュール分離。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行して例外を伝播。

Other notable points
- ルックアヘッドバイアス対策
  - score_news / score_regime / factor 等の処理は datetime.today()/date.today() に依存せず、呼び出し側が与える target_date を基準としてウィンドウを決定する設計。
  - DB クエリは target_date 未満 / 排他条件を用いる等、将来データの混入を防止。

- 冗長性・堅牢性
  - OpenAI API 呼び出しの例外ハンドリング（RateLimitError / APIConnectionError / APITimeoutError / APIError）とリトライロジックを幅広く実装。
  - API レスポンスパース失敗や未知コードは警告ログを出してスキップ（例外は基本的に上げない設計）。
  - DuckDB のバージョン互換性に配慮した実装（executemany の空リスト回避等）。

Fixed
- DuckDB executemany に対する互換性対策を実装（空リストを渡す前にチェックしてエラー回避）。
- OpenAI レスポンスの JSON パース失敗や 5xx 系例外発生時に、フェイルセーフで 0.0 を返す・スキップするように安定化。

Security
- .env 読み込みで OS 環境変数を上書きしないデフォルト動作と、protected set による上書き禁止実装により、プロセス環境の安全性を確保。
- OpenAI API キーや各種トークンは Settings を通じて必須パラメータとして扱い、未設定時は ValueError を送出して明示的に対処するように設計。

Compatibility
- DuckDB をデータバックエンドとして想定（DuckDB の日付型/executemany の挙動に配慮）。
- OpenAI SDK（chat completions）を利用。gpt-4o-mini + JSON mode を前提。

Notes / TODO（コードから推測）
- jquants_client、quality モジュール、execution / monitoring モジュールは参照されているが本差分に含まれていない（別モジュール/パッケージとして提供想定）。
- 将来的な改善案としては、より詳細な監査ログ、ネットワーク層の共通リトライユーティリティ、テストカバレッジの拡充等が考えられる。

注記
- 本 CHANGELOG は提供されたソースコードから実装内容・設計方針を推測して作成しています。実際の変更履歴（開発コミットログ等）とは差異がある場合があります。