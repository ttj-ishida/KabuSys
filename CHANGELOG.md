CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ全体
  - 初期公開バージョンを追加。パッケージ名: kabusys (バージョン 0.1.0)。
  - パッケージ公開インターフェースを定義（src/kabusys/__init__.py: data, strategy, execution, monitoring をエクスポート）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
    - 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書きされない。
  - .env パーサーは以下をサポート:
    - export KEY=val 形式
    - シングル / ダブルクォートとバックスラッシュのエスケープ
    - 行末コメントの扱い（クォート外での '#' を適切に認識）
    - 無効行（空行・コメント・= がない行）は無視
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得可能:
    - J-Quants / kabuステーション / Slack トークン、チャネル等の必須設定（未設定時は ValueError を投げる）
    - DB パス (DuckDB / SQLite)、監視用 PID ファイルパス
    - リソース閾値（CPU / メモリ / ディスク）、環境 (development/paper_trading/live)、ログレベル検証

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信してセンチメントスコアを取得。
    - 処理の主要設計:
      - ニュースウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
      - 1 回の API コールは最大 20 銘柄（_BATCH_SIZE）を処理。
      - 1 銘柄につき最新 10 件かつ最大 3000 文字でトリム。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
      - レスポンス検証（JSON 構文・results リスト・各要素の code/score・スコア数値化）を実施。無効レスポンスはスキップ。
      - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時は他銘柄スコアを保護）。
    - テスト時に OpenAI 呼び出しを差し替え可能（_call_openai_api をパッチ可能）。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離と、マクロ経済ニュースの LLM センチメントを組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - アルゴリズムと設計:
      - ma200_ratio（最新終値 / MA200）を計算（target_date 未満のデータのみ使用、ルックアヘッド防止）。
      - マクロ記事はキーワードでフィルタ（_MACRO_KEYWORDS）、最大 20 件まで取得し LLM で -1.0〜1.0 の macro_sentiment を取得。
      - 合成スコア = clip(0.7 * MAスコア + 0.3 * macro_sentiment, -1, 1)（重み: MA 70%、マクロ30%、MA は scale で調整）。
      - 閾値に基づきラベル付与（_BULL_THRESHOLD / _BEAR_THRESHOLD）。
      - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で、失敗時は ROLLBACK（さらに ROLLBACK失敗のログ対応）。
      - API 失敗時は macro_sentiment=0.0 のフェイルセーフ挙動。
    - OpenAI クライアント呼出しはニュース NLP と意図的に別実装で分離。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの管理、営業日判定、次/前営業日の算出、期間内営業日リスト取得、SQ 日判定を提供。
    - 設計方針:
      - market_calendar が未取得時は曜日ベースでフォールバック（平日を営業日と扱う）。
      - DB に登録済みの値を優先し、未登録日は曜日ベースで補完することで一貫性を保持。
      - 探索は最大 _MAX_SEARCH_DAYS 日まで（無限ループ防止）。
      - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得・バックフィル・健全性チェック）。
  - pipeline / ETLResult (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装。ETL の実行結果（取得数・保存数・品質問題リスト・エラー概要）を格納し、辞書化メソッド to_dict を提供。
    - ETL 実行の基本方針（差分取得、idempotent 保存、品質チェックは収集して呼び出し元判断など）を定義。
    - etl.py から ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum / Volatility / Value 等の定量ファクター計算を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA が不足する場合は None）
      - calc_volatility: 20日 ATR の平均、相対 ATR、20日平均売買代金、出来高比率等
      - calc_value: EPS・ROE を組み合わせた PER、ROE（最新の raw_financials を target_date 以前の最新で参照）
    - DuckDB SQL を用い、prices_daily / raw_financials テーブルのみを参照。
    - 結果は (date, code) を含む dict のリストで返却。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns: 任意ホライズンの fwd_Nd を複数同時算出）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関）、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。入力の妥当性チェック（horizons の制約など）を実施。
  - research パッケージ __init__ で主要関数を再エクスポートし、zscore_normalize を data.stats から参照可能に。

- ロギング / エラーハンドリング
  - 各モジュールで詳細な情報ログ・警告ログを実装し、API エラー/パースエラーはフェイルセーフにより処理継続（必要に応じて warnings / logger.warn）。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 全ての日時処理で datetime.today()/date.today() を直接参照せず、関数引数で target_date を受ける設計を優先。
- OpenAI 呼び出し: JSON モードを利用し、レスポンスパースと検証に重きを置く。失敗時は例外を投げず安全側のデフォルト（0.0 等）にフォールバックする箇所がある。
- DB 操作: DuckDB を使用。INSERT/DELETE の実行は冪等性を意識（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK）している。DuckDB の executemany に関する互換性注意（空リスト渡し不可）に配慮。
- テスト容易性: OpenAI 呼出箇所は内部関数をモック可能に設計。

Security
- 機密情報（API キー・トークン）は環境変数経由で取得。Settings の必須プロパティは未設定時に明示的なエラーを投げ、誤設定を早期に検出。

Deprecated
- なし

Removed
- なし

Fixed
- 初回リリースのため該当なし

----

今後の予定（短期）
- strategy / execution / monitoring の実装と統合テスト
- ドキュメント（API 使用例、運用手順、環境変数テンプレート .env.example）追加
- CI/テスト環境での OpenAI 呼出しのモック整備とレート制御検証

（以上）