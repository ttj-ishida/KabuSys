CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で宣言。

- 環境設定（src/kabusys/config.py）:
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探す方式で実装（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサーは以下に対応:
    - 空行 / コメント行（#）の無視、"export KEY=val" 形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォートなし値のインラインコメント処理（# の直前が空白またはタブのときのみコメントとして扱う）。
  - _load_env_file に override/protected（OS 側のキー保護）オプションを実装。
  - Settings クラスを公開:
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを提供（必須項目は _require() で検査し未設定時は ValueError を送出）。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）や LOG_LEVEL の検証を実装。
    - duckdb/sqlite のパスを Path オブジェクトで返すユーティリティを提供。
    - .is_live/.is_paper/.is_dev の便利プロパティを実装。

- AI モジュール（src/kabusys/ai）:
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None) を実装。
      - タイムウィンドウの計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換して扱う）。
      - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1 銘柄あたり最大記事数・文字数でトリム）。
      - OpenAI(gpt-4o-mini) に対してバッチ送信（最大 20 銘柄/コール）。
      - レスポンスのバリデーション（JSON パース、results 配列、code/score の検証、数値のクリップ）。
      - DuckDB への冪等書き込み（DELETE → INSERT、executemany を利用、部分失敗時に既存データを保護）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
      - API キー未指定時は ValueError を送出。
    - テスト容易性のため _call_openai_api は patch して差し替え可能。
    - スコアは ±1.0 にクリップ。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None) を実装。
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（直近 200 行）を計算。
      - raw_news からマクロ経済キーワードに一致するタイトルを取得（最大 20 件）。
      - OpenAI(gpt-4o-mini) でマクロセンチメントを JSON 出力（{"macro_sentiment": float}）で取得。
      - 指定重み（MA70% / Macro30%）でレジームスコアを合成し clip(-1,1)。
      - 閾値により regime_label を bull/neutral/bear に分類。
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試みて例外を再送出）。
      - LLM API の失敗時は macro_sentiment=0.0 をフェイルセーフとして使用（例外を投げず処理継続）。
      - API キー未指定時は ValueError を送出。
    - 内部の OpenAI 呼び出しは news_nlp と独立実装（モジュール間結合を避ける設計）。

- リサーチ（src/kabusys/research）:
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value の各ファクター計算関数を実装。
      - calc_momentum: mom_1m/mom_3m/mom_6m、および ma200_dev（200 日 MA 乖離）。
      - calc_volatility: 20 日 ATR の算出、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から最新の財務データを取得し PER/ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB の SQL ウィンドウ関数を活用し営業日ベースのラグを計算。
    - データ不足時は None を返す挙動。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を使用）を計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。利用可能レコードが 3 未満なら None。
    - rank(values): 同順位は平均ランクのランク付けを実装（浮動小数の丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリを実装。
  - research パッケージの __all__ で主要関数を再エクスポート（zscore_normalize は data.stats から）。

- データプラットフォーム（src/kabusys/data）:
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理ロジックを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
      - market_calendar テーブルが未取得の場合は曜日ベース（週末は非営業日）でフォールバック。
      - next/prev/search は最大探索長を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
      - calendar_update_job(conn, lookahead_days): J-Quants クライアントを使った差分取得・保存処理を実装。バックフィル・健全性チェックあり。
  - pipeline（src/kabusys/data/pipeline.py）
    - ETL パイプライン用のユーティリティと ETLResult データクラスを実装。
      - ETLResult: ETL 実行結果の構造（取得数/保存数/品質問題/エラー一覧）と to_dict() を提供。
      - 差分取得ロジック、バックフィル日数、品質チェックのフック（quality モジュール参照）を想定した設計。
      - DuckDB のテーブル最大日付取得などの内部ユーティリティを提供。
  - etl パッケージ: pipeline.ETLResult を data.etl で再エクスポート。

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を主要ロジック内で直接参照しない（関数引数で target_date を受ける）。
  - DuckDB を主要なデータ格納/分析基盤として想定（SQL と Python 混在実装）。
  - 外部 API 呼び出し（OpenAI / J-Quants）はフェイルセーフ設計: 一部失敗時はログ出力して処理継続、重度の DB 書き込み失敗等は上位へ例外伝播。
  - テスト容易性: OpenAI 呼び出し部分は内部関数を patch 可能にして単体テスト容易化。

Fixed
- 初回リリースのため Fix は特になし（実装時点での堅牢化措置を複数実装）。
  - LLM 呼び出しのエラーに対するリトライ/バックオフや JSON パース失敗時の復元（最外の {} 抽出）など、運用上の問題を想定した耐性を実装済み。

Security
- 環境変数の取り扱いに注意:
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / OPENAI_API_KEY 等の必須トークンは Settings で必須チェックを行い、未設定時は ValueError を送出する。
  - .env 自動ロード時に既存 OS 環境変数を保護する機構（protected set）を導入。

Notes / Known behaviors
- OpenAI モデルは gpt-4o-mini を指定（JSON Mode を利用）。
- news_nlp のバッチサイズ上限は 20、1 銘柄あたりの最大文字数は 3000、最大記事数は 10。
- regime_detector のマクロキーワードや重みはソースコード内の定数で管理されており、必要に応じて調整可能。
- score_news / score_regime は API キーが未指定の場合 ValueError を送出するため、呼び出し側で適切に注入すること（api_key 引数または環境変数 OPENAI_API_KEY）。
- DB 書き込みは冪等化を意識した実装（DELETE→INSERT のパターン、ON CONFLICT を想定）で、部分失敗時に既存データを保護する設計を採用。

作者メモ
- 今後の作業候補:
  - strategy / execution / monitoring の実装拡充（現在はパッケージ公開のみ）。
  - 詳細な単体テスト群の追加（特に外部 API 呼び出しのモックを用いた回帰テスト）。
  - ドキュメント（Usage / Deployment / Operation runbook）の整備。