CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
----------

- （なし）

0.1.0 - 2026-04-02
------------------

Added
- 初回リリース。主要コンポーネントを実装。
  - パッケージ基盤
    - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール指定）
  - 設定 / 環境変数管理（src/kabusys/config.py）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
    - export KEY=val 形式やクォート・コメントの柔軟なパース実装
    - 既存 OS 環境変数を保護する protected 機能（.env 上書き制御）
    - 必須環境変数取得ヘルパー（_require）と Settings クラス（J-Quants, kabu, Slack, DB パス, 監視閾値, env/log_level 等のプロパティ）
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値セットでバリデーション）
  - データ関連（src/kabusys/data/*）
    - カレンダー管理（calendar_management.py）
      - market_calendar を使った営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
      - DB 未取得時は曜日ベースのフォールバック（週末除外）
      - JPX カレンダー差分取得ジョブ（calendar_update_job）実装（J-Quants クライアント呼び出し／バックフィル・健全性チェック付）
      - market_calendar の存在判定や DuckDB 日付変換ユーティリティ
    - ETL（pipeline.py / etl.py）
      - ETLResult データクラス（ETL 実行結果保持、品質問題・エラー集約）
      - 差分更新・バックフィルの設計、DuckDB を用いた idempotent 保存想定（jquants_client 経由）
      - テーブル存在チェック・最大日付取得等ユーティリティ
  - AI 関連（src/kabusys/ai/*）
    - ニュース NLP（news_nlp.py）
      - タイムウィンドウ計算（calc_news_window: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
      - raw_news / news_symbols を銘柄単位で集約し、銘柄ごとに最大記事数／文字数でトリム
      - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄／チャンク）、JSON mode を利用
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ
      - レスポンス検証（results 配列・code/score の整合性検査）とスコア ±1 へのクリップ
      - DuckDB の executemany 空リスト回避（部分書き換えロジック: DELETE→INSERT）
      - テストで差し替え可能な _call_openai_api フック
    - 市場レジーム判定（regime_detector.py）
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付け合成（70% / 30%）して日次レジーム（bull/neutral/bear）を判定
      - prices_daily / raw_news を使ったデータ取得、calc_news_window を利用したウィンドウ処理
      - OpenAI 呼び出し（gpt-4o-mini）とリトライロジック、API 失敗時は macro_sentiment=0.0 でフォールバック
      - 結果の冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
  - リサーチ / ファクター（src/kabusys/research/*）
    - factor_research.py
      - Momentum（mom_1m/mom_3m/mom_6m）、ma200_dev（200日MA乖離）、ATR、流動性指標、出来高関連を DuckDB SQL で計算する関数群（calc_momentum, calc_volatility, calc_value）
      - raw_financials からの EPS/ROE 取得を用いた PER / ROE 計算（データ不足時は None）
      - DuckDB を活用したウィンドウ関数・集約により実装
    - feature_exploration.py
      - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）
      - IC（Information Coefficient）計算（calc_ic）: ランク相関（Spearman）実装、必要件数未満は None を返す
      - ランク変換ユーティリティ（rank）: 同順位は平均ランクで処理
      - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算
    - research パッケージ __all__ に主要ユーティリティをエクスポート
  - DB/外部ライブラリ
    - DuckDB を主要な分析・保存 DB として利用する設計を採用

Changed
- 設計ポリシー（コード内ドキュメントとして記載）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照せず、target_date を明示的に受け渡す設計
  - 外部 API 失敗時はシステム全体を停止させずフォールバックする方針（LLM 失敗時は 0.0 で継続等）
  - モジュール間の結合を避けるため、OpenAI 呼び出し等は各モジュール内で独立実装（テスト用の差し替えフックを提供）

Fixed
- 安全性・互換性の細かな対応
  - .env パーサーのクォート・エスケープ・コメント処理実装により実運用上の .env フォーマット差異に耐性を持たせた
  - DuckDB の executemany に関する空リスト制約を回避するため、書き込み前に空チェックを行う実装
  - API エラー判定で status_code の有無に対応する堅牢化（getattr を使用）

Security
- 環境変数の取り扱い改善
  - OS 環境変数を protected として .env による上書きを防止
  - 必須環境変数未設定時は明確なエラーメッセージを送出（_require）
- OpenAI API キーを明示的に引数注入可能（api_key 引数または OPENAI_API_KEY 環境変数）

Notes / Known limitations
- 一部外部クライアント（jquants_client 等）はこの差分に依存しており、実運用には各クライアントの実装が必要
- OpenAI への呼び出しは gpt-4o-mini + JSON Mode を前提としているため、別モデルやレスポンス形式を用いる場合はレスポンス検証ロジックを調整する必要あり
- DuckDB 日付型の取り扱い・バインド挙動はバージョン差に敏感なため、運用時に互換性検証を推奨

--- 

この CHANGELOG はコードベース（src/ 以下）の実装から推測して作成しています。実際のリリースノート作成時にはコミット履歴・リリースノート方針に沿って調整してください。