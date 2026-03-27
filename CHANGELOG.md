Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに準拠します。

0.1.0 - 2026-03-27
=================

Added
-----
- パッケージ初回公開
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。バージョン: 0.1.0、公開 API: data, strategy, execution, monitoring。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動環境変数読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env の行パーサを強化：
    - export プレフィックス対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォートの有無に応じた正しい扱い）。
  - 環境変数取得ヘルパ（_require）と Settings クラスを提供：
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル のプロパティを用意。
    - env / log_level の値検証（許容値チェック）。
    - duckdb/sqlite のパスはデフォルトを用意し expanduser を適用。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得し ai_scores テーブルへ保存する一連のパイプラインを実装。
  - タイムウィンドウ定義（JST 前日15:00～当日08:30、内部は UTC naive datetime を使用）。
  - チャンク処理（1コールあたり最大 20 銘柄）、1銘柄あたりの記事上限/文字数トリム（最大記事数 10、最大文字 3000）を実装してトークン肥大化に対処。
  - OpenAI 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）をエクスポネンシャルバックオフで実装。その他エラーはスキップフェイルセーフ。
  - レスポンスの厳密なバリデーション実装（JSON の抽出/パース、results リスト、code と score の検証、数値検査、スコアの ±1.0 クリップ）。
  - 書き込みは部分置換方式（対象コードのみ DELETE → INSERT）で冪等性と部分失敗時の保護を実現。DuckDB executemany の空リスト問題に対するガードも実装。
  - テスト容易性のため OpenAI API 呼び出し部分を内部でラップし patch 可能（_call_openai_api）。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を算出・保存するロジックを実装。
  - マクロニュース抽出は news_nlp の calc_news_window と raw_news を利用し、キーワードフィルタリング（日本／米国キーワード群）を実装。
  - OpenAI 呼び出しは独立実装で、リトライ・フォールバック（API 失敗時は macro_sentiment = 0.0）を実装。
  - スコア合成・閾値によるラベル付け（bull / neutral / bear）を行い、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す挙動。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。PBR/配当利回りは未実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証（正の整数かつ <= 252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。レコード不足（<3）や等分散時は None を返す。
    - rank: 平均ランク（タイの平均ランク）実装（浮動小数の丸めで ties 検出の堅牢化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を純標準ライブラリで計算。
  - 上記ユーティリティは外部ライブラリに依存せず DuckDB を直接利用する設計。

- データプラットフォーム（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時のフォールバック（曜日ベース、土日を非営業日）を実装。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装（直近バックフィル、未来日付の過剰チェック）。
  - pipeline / ETL:
    - ETLResult データクラスを導入（取得数/保存数/品質問題/エラー一覧等を保持）。to_dict により品質問題をシリアライズ可能。
    - 差分更新ロジックのための内部ユーティリティ（_table_exists, _get_max_date 等）。
    - デフォルトのバックフィル日数やカレンダー先読み等の定数設定を導入。
  - data.etl は pipeline.ETLResult を再エクスポート。

- インフラ・共通
  - DuckDB を主要なストレージインターフェースとして採用し、SQL と Python を組み合わせた処理を実装。
  - OpenAI SDK（OpenAI クライアント）を利用した JSON mode での LLM 結果取得と堅牢な応答パース処理。
  - ロギング・例外ハンドリングを多用し、フェイルセーフ（API失敗時は無害化して処理継続）を重視した実装。
  - ルックアヘッドバイアス防止設計:
    - 各スコア算出関数は内部で datetime.today() / date.today() を参照しない。
    - DB クエリにおいて target_date 未満（排他）や target_date 以前の最新値を用いる等の配慮。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Notes / 使用上の注意
-------------------
- OpenAI API キーは api_key 引数で注入するか、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
- .env 読み込みはプロジェクトルート探索に基づくため、パッケージ配布後でも動作するように設計されています。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- ai 系の出力（news_nlp / regime_detector）は LLM の出力に依存するため、外部 API エラーや不正レスポンスを考慮したフォールバック（スコア 0.0、空スコアのスキップ等）を行います。
- 一部機能（calc_value の PBR・配当利回り等）は未実装です。将来的な拡張対象です。
- DuckDB の executemany に対する互換性に配慮したガードを実装しています（空リストを渡さない等）。

今後の予定（短期）
-----------------
- 研究/戦略モジュール（strategy）と発注実行（execution）、監視（monitoring）の実装拡張と統合テストの追加。
- ai モデルへの問い合わせ最適化（プロンプト改善、バッチ戦略の見直し）。
- ETL の品質チェック（quality モジュール）の更なる強化とレポーティング機能の追加。

著記
----
この CHANGELOG は、提供されたコードを基に機能追加と実装上の注意点を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それを優先してください。