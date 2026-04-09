Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」方式に準拠します。

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初期リリース: kabusys (KabuSys) — 日本株自動売買・データ基盤・リサーチ支援用ライブラリの初期実装。
- パッケージ公開インターフェース:
  - src/kabusys/__init__.py で version と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定／環境変数管理:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export プレフィックス、シングル／ダブルクォート、エスケープ、行コメントを考慮した堅牢な実装。
    - .env.local は .env を上書きするが OS 環境変数は保護（保護セットに含まれるキーは上書きしない）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定プロパティを定義。
    - 各種バリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の許容値チェック）。
    - パス類は Path オブジェクトで返却（expanduser を適用）。
    - 必須環境変数未設定時は明確な ValueError を発生。
- AI 関連（OpenAI 統合）:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを銘柄ごとに集約し、gpt-4o-mini（JSON Mode）で銘柄別センチメントを評価して ai_scores テーブルへ書込む機能（score_news）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を実装（JST 基準のウィンドウを UTC に変換）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／回）、記事トリム（最大記事数・最大文字数）を実装しトークン爆発対策。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。致命的な失敗はスキップして継続（フェイルセーフ設計）。
    - OpenAI レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、スコアクリップ、未知コードの無視）。
    - テスト向けに _call_openai_api を patch 可能に実装。
    - DuckDB の executemany の制約に配慮した書込み（空リストを渡さないガード）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200 比率算出（ルックアヘッド防止のため target_date 未満のみ使用）、マクロ記事の抽出、OpenAI 呼び出し、スコア合成、冪等的な DB 書き込みをサポート。
    - API エラー時は macro_sentiment を 0.0 にフォールバック。OpenAI 呼び出しは独立実装でモジュール結合を避ける（テスト容易性）。
- データ基盤（Data）:
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休場）を行う堅牢な実装。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得・保存、バックフィル、健全性チェックを実装。
    - DuckDB 日付型取り扱いユーティリティと最大探索日数制限で無限ループを防止。
  - src/kabusys/data/pipeline.py / etl.py
    - ETL パイプライン設計に基づく ETLResult データクラスを実装（取得/保存件数、品質問題、エラー集約、シリアライズ用 to_dict）。
    - pipeline モジュールの ETLResult を data.etl から再エクスポート。
    - 差分更新、backfill、品質チェック（quality モジュール連携）を想定した設計。
- リサーチ（Research）:
  - src/kabusys/research/factor_research.py
    - ファクター計算ユーティリティを実装: calc_momentum（1M/3M/6M リターン、ma200 乖離）、calc_volatility（20日 ATR・相対ATR・20日平均売買代金・出来高比率）、calc_value（PER, ROE を raw_financials と組合せて算出）。
    - DuckDB のウィンドウ関数を用いた効率的な実装と欠損値取り扱い（データ不足時は None を返す）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons の検証）、IC 計算 calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を最小化して標準ライブラリのみで集計ロジックを実装。
  - src/kabusys/research/__init__.py で上記関数を再輸出。
- DuckDB を主要なデータストアとして前提（関数の引数に DuckDB 接続を受け取る設計）。
- ロギング: 主要処理に対して情報/警告/例外ログを適切に出力する実装。

Changed
- n/a（初回リリースのため履歴は追加のみ）

Fixed
- n/a（初回リリースのため履歴は追加のみ）

Security
- API キー・パスワード等は Settings から必須チェックを行い、未設定時は明示的なエラーを返す。環境変数読み込み時に OS 環境変数を保護する設計。

Notes / Limitations
- news_nlp の出力は現状 sentiment_score と ai_score を同値として扱う（将来的に差分を付ける可能性あり）。
- calc_value は PBR・配当利回りなどは未実装（README / StrategyModel.md に基づいたフェーズ実装）。
- OpenAI 連携は gpt-4o-mini を想定し JSON Mode を利用する想定。実際の API 挙動やモデル変更によりパース処理の調整が必要となる可能性あり。
- DuckDB executemany に対する空リスト制約に配慮した実装を行っている（互換性確保のため）。

将来の予定（例）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジック・ブローカークライアントの実装。
- 追加の品質チェックルールと品質レポート出力。
- テスト向けのモッククライアント・CI ワークフロー整備。

問い合わせ / 貢献
- バグ報告・機能提案は issue を立ててください。Pull Request は歓迎します。