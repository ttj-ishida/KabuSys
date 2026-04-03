CHANGELOG
=========
すべての変更は Keep a Changelog のフォーマットに準拠しています。
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース: KabuSys 日本株自動売買支援ライブラリを公開。
  - パッケージ情報
    - src/kabusys/__init__.py によるパッケージ初期化。__version__ = 0.1.0。
    - __all__ で主要サブパッケージをエクスポート: data, strategy, execution, monitoring（実装の出口を想定）。

  - 環境設定 / ロード
    - src/kabusys/config.py
      - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD に依存しない）。
      - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
      - .env ロードの優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は protected として上書き回避。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - Settings クラスを提供（settings インスタンス経由で設定値を取得）。
        - J-Quants / kabu ステーション / LINE / DB パス / 監視閾値等の設定プロパティを提供。
        - KABUSYS_ENV および LOG_LEVEL の検証（許容値チェック）を実装。
        - is_live / is_paper / is_dev のユーティリティプロパティを提供。

  - AI（ニュース NLP / 市場レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを評価し ai_scores テーブルへ書き込む。
      - ニュース収集ウィンドウ計算（JST基準）: calc_news_window を提供（UTC naive datetime を返す）。
      - バッチ送信（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - OpenAI 呼び出しは JSON Mode を利用、レスポンスのバリデーションを厳格に行いスコアを ±1.0 にクリップ。
      - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。致命的でない失敗はスキップして処理継続（フェイルセーフ）。
      - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性と部分失敗時の保護を確保。DuckDB 0.10 の executemany 空配列問題に配慮。
      - テスト用に _call_openai_api をモック可能。

    - src/kabusys/ai/regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルに書き込む（冪等）。
      - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
      - マクロニュース抽出はキーワードベース（_MACRO_KEYWORDS）でタイトルを選出し、OpenAI で macro_sentiment を算出。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
      - API 呼び出し失敗時はフォールバック（macro_sentiment=0.0）。OpenAI エラーに対するリトライ/バイパス挙動を実装。
      - 設定された閾値に基づき regime_label を bull/neutral/bear に分類。
      - DB 操作は BEGIN/DELETE/INSERT/COMMIT の枠組みで冪等性確保。エラー時は ROLLBACK を試行して例外を伝播。

    - エクスポート
      - src/kabusys/ai/__init__.py で score_news を公開（将来的に他関数も追加想定）。

  - Data（ETL / カレンダー / パイプライン）
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー管理機能を実装。
      - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - DB の market_calendar を優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）を用いる一貫性あるロジック。
      - next/prev_trading_day は最大探索日数（_MAX_SEARCH_DAYS）で打ち切り、無限ループ防止。
      - calendar_update_job(conn, lookahead_days)：J-Quants から差分取得して market_calendar を冪等的に保存。バックフィル・健全性チェック実装。
      - jquants_client 経由の fetch/save を使用。

    - src/kabusys/data/pipeline.py
      - ETL パイプラインのためのユーティリティと結果データクラス ETLResult を実装。
      - ETLResult: 取得/保存件数、品質チェック結果（quality.QualityIssue）やエラー一覧を格納。has_errors / has_quality_errors / to_dict を提供。
      - 差分更新・バックフィル・品質チェック方針に基づく設計（概念説明と定数）。
      - 内部ユーティリティ: テーブル存在確認や最大日付取得等の下地実装（_table_exists, _get_max_date 等、一部実装あり）。
      - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - Research（ファクター計算 / 特徴量探索）
    - src/kabusys/research/factor_research.py
      - ファクター計算関数を実装:
        - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev（200日MA乖離）を計算。
        - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR/平均売買代金は窓サイズ条件付きで None を返す挙動）。
        - calc_value(conn, target_date): raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損の場合は None）。
      - DuckDB 上で SQL ウィンドウ関数を活用し営業日ベースの計算。データ不足時は None を返す方針。
      - 出力は (date, code) をキーとする dict のリスト。

    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり（horizons は 1..252 の正整数）。
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。有効レコード3件未満で None を返す。
      - rank(values): 同順位は平均ランクで扱うランク化ユーティリティ（丸め処理により ties を検出）。
      - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ機能。
      - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から参照）。

  - 共通設計方針（全体）
    - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
    - 外部 API 呼び出し（OpenAI / J-Quants）は呼び出し元でキー注入が可能（api_key 引数）にしてテスト容易性を確保。
    - DuckDB を主要なローカル分析 DB として使用。SQL + Python のハイブリッド実装。
    - API 呼び出しに対してはリトライ・バックオフ・フォールバックを実装し、部分失敗が全体を停止させない保守的な運用を想定。

Security
- 環境変数の取り扱いに注意:
  - .env 読み込み時は既存 OS 環境変数を protected として上書きを避ける挙動を実装。
  - OPENAI_API_KEY 等の機密トークンは環境変数での注入を想定。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Fixed
- 初版リリースのため該当なし。

Changed / Deprecated / Removed
- 初版リリースのため該当なし。

Notes / 今後の作業候補
- strategy, execution, monitoring サブパッケージは __all__ に含まれているが、本差分においては具体的機能の定義・実装が限定的（今後の追加を想定）。
- テスト補助: OpenAI 呼び出し箇所はモックしやすい設計になっているが、ユニットテスト例や CI 連携の追加が必要。
- ドキュメント: API 使用例・運用手順（.env.example、DB スキーマ、jquants_client の設定）を README / docs に整備予定。