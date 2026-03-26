CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-26
--------------------

Added
- 初回公開リリース: kabusys パッケージ v0.1.0
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
    - パブリックサブパッケージ: data, strategy, execution, monitoring（__all__ 指定）

  - 環境変数 / 設定管理（src/kabusys/config.py）
    - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env パーサはコメント・export 構文・シングル/ダブルクォート・バックスラッシュエスケープに対応
    - 環境変数の保護: OS 環境変数は protected として上書きを防止
    - 必須設定取得のヘルパ: Settings クラス（J-Quants / kabu / Slack / DB パス / システム設定）
      - 設定値の検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG..CRITICAL）
      - デフォルト値: KABUSYS_ENV=development, KABU_API_BASE_URL=http://localhost:18080/kabusapi, DB パスなど
      - settings = Settings() を公開

  - AI モジュール（src/kabusys/ai/）
    - ニュース NLP（news_nlp.py）
      - raw_news + news_symbols を銘柄別に集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み
      - バッチサイズ制御（最大 20 銘柄）、記事数・文字数トリム、JSON Mode 出力のバリデーション
      - リトライ戦略: 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ
      - フェイルセーフ: API 失敗時は個別チャンクをスキップして処理継続
      - テスト容易性: _call_openai_api をモック可能に実装
      - タイムウィンドウ計算ユーティリティ: calc_news_window（JST → UTC の変換、明確な閉区間/開区間）
    - 市場レジーム判定（regime_detector.py）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
      - マクロニュース抽出（マクロキーワードリスト）、LLM 呼び出し（gpt-4o-mini）、リトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）
      - レジームスコア合成と ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみ参照）
      - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションの ROLLBACK 保護
      - テスト容易性: _call_openai_api をモック可能に実装
    - 共通設計方針
      - LLM 呼び出しは明示的な api_key 注入をサポート（api_key 引数 or 環境変数 OPENAI_API_KEY）
      - ルックアヘッドバイアス防止のため date.today() / datetime.today() を評価に使わない設計

  - データ処理（src/kabusys/data/）
    - カレンダー管理（calendar_management.py）
      - JPX カレンダー（market_calendar）の読み書き、営業日 / 前後営業日の判定、期間内営業日取得、SQ 日判定
      - DB が空の場合は曜日ベース（土日除外）でフォールバックする一貫した挙動
      - next_trading_day / prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止
      - 夜間バッチ job（calendar_update_job）: J-Quants クライアントから差分取得 → 保存（バックフィル / 健全性チェック）
    - ETL パイプライン（pipeline.py）
      - 差分更新、idempotent 保存（jquants_client の save_* を利用）、品質チェックの集約
      - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラーの集計・to_dict）
      - テストしやすさと互換性を重視（DuckDB の executemany の挙動考慮、最終日取得ユーティリティなど）
    - etl モジュールは ETLResult を再エクスポート（data/etl.py）

  - 研究用ユーティリティ（src/kabusys/research/）
    - factor_research.py
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB 上で計算
      - 入力: prices_daily / raw_financials（外部 API 呼び出しなし）
      - 不足データ時は None を返す等の安全設計
    - feature_exploration.py
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ / ランク相関）、ファクター統計サマリ
      - pandas 等に依存せず標準ライブラリで実装
      - rank 関数は同順位を平均ランクにする実装（丸め対策あり）

  - パッケージ再エクスポート
    - research パッケージは主要関数を __all__ で公開（zscore_normalize, calc_momentum 等）

Security / Reliability / Design notes
- 外部 API 呼び出し（OpenAI, J-Quants）は堅牢なリトライとフェイルセーフを実装。API エラー時は例外を直接投げずにロギングして部分継続する箇所が多く、バッチ処理の耐障害性を重視
- DB 書き込みは可能な限り冪等化（DELETE → INSERT や ON CONFLICT を想定）し、トランザクション失敗時の ROLLBACK を試行
- ルックアヘッドバイアス防止: 日付処理は target_date を明示的に受け取り、現在時刻を暗黙に参照しない方針
- テストしやすさ: OpenAI 呼び出しやその他外部依存点をモック可能に実装

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Notes
- デフォルトの DB ファイルパスなどは Settings で定義されており、環境変数で上書き可能
- OpenAI モデル名や各種閾値・バッチサイズはソース内定数として明示的に管理されている（将来のチューニングが容易）

Contributing
- バグ報告・機能追加提案はリポジトリの issue を通して行ってください。