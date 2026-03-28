# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で明示。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを判定（CWD 非依存）。
  - .env 行パーサー実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートなしでは直前に空白/タブがある `#` をコメントと判定）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラスに各種プロパティを提供（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベルなど）。
  - 必須環境変数未設定時は明示的な ValueError を送出する _require() を提供。
  - KABUSYS_ENV の検証（development/paper_trading/live）および LOG_LEVEL の検証（DEBUG〜CRITICAL）。

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を使い、記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチ処理、チャンクサイズ制御（最大20銘柄／チャンク）、1銘柄あたりの記事数・文字数制限を実装。
    - JSON Mode を利用した厳密な JSON レスポンス期待と冗長テキストからの復元ロジック。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装（再試行回数制限あり）。
    - レスポンス検証（results 配列、code の一致、数値チェック）とスコア ±1.0 のクリップ。
    - DuckDB への書き込みは部分成功を想定して、書き込み対象コードのみ DELETE → INSERT の置換ロジック（冪等性＆部分失敗保護）。
    - API キー未設定時は ValueError を送出。API 呼び出しはテスト時にモック差し替え可能な private 関数を介して行う設計。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（TOPIX/日経225連動ETF）を用いた 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出。
    - マクロニュース抽出（キーワードベース）、OpenAI（gpt-4o-mini）を用いたセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを提供。
    - LLM の失敗時はフェイルセーフとして macro_sentiment=0.0 を使用し処理継続。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
  - ai/__init__.py で score_news を再エクスポート。

- データ管理（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得・保存・品質チェック（quality モジュール連携）を想定した ETLResult データクラスを実装。
    - ETLResult.to_dict() により品質問題を (check_name, severity, message) の辞書リストに変換。
    - DuckDB 上の最大日付取得やテーブル存在チェック等のユーティリティを実装。
    - backfill、calendar lookahead、品質チェックの重大度フラグなど設計方針をコードに反映。
    - ETLResult を外部公開（src/kabusys/data/etl.py）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定、次/前営業日の算出、期間内営業日リスト取得などのユーティリティを提供。
    - カレンダー未取得時の曜日ベースフォールバック（週末を非営業日）を採用。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を使用）。
    - 異常検出（将来日付の健全性チェック）やバックフィルの実装。
  - DuckDB 周りの実装で DuckDB の executemany の空リスト制約を考慮した安全な書き込み手順を採用。
  - data パッケージをエントリポイントとして用意（src/kabusys/data/__init__.py）。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 差分）、Volatility（20日 ATR 等）、Value（PER/ROE）等の計算関数を実装。
    - DuckDB ベースの SQL と Python を組み合わせた実装。外部 API 呼び出しは行わない。
    - 関数: calc_momentum(conn, target_date), calc_volatility(...), calc_value(...)
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）: calc_forward_returns(conn, target_date, horizons=None)
    - IC（Spearman rank）計算: calc_ic(...)
    - ランク変換ユーティリティ: rank(values)
    - ファクター統計サマリ: factor_summary(records, columns)
  - research パッケージの __init__.py で主要関数を集約して再エクスポート。

### 信頼性 / 安全性
- DB 書き込みは明示的なトランザクション制御（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）を行い、部分失敗時に既存データを保護する設計。
- AI 関連の API 呼び出しはリトライ・バックオフ・5xx 判定等ロバストに実装され、非致命的な失敗はログ出力の上でフェイルセーフなデフォルト値（0.0 など）にフォールバックする。
- ルックアヘッドバイアス対策: 各アルゴリズム（news/regime/factor 等）は datetime.today()/date.today() を内部参照せず、呼び出し側が target_date を与える設計。

### 制約・既知の事項
- OpenAI API（gpt-4o-mini）を利用するため、OPENAI_API_KEY の設定が必須（score_news/score_regime は未設定時に ValueError）。
- DuckDB のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が前提。スキーマ未作成時の挙動は関数により異なる（多くは空結果や None を返す）。
- 現時点では Strategy / Execution / Monitoring の実装詳細はパッケージ構成で公開しているが（__all__）、本差分では主にデータ・リサーチ・AI 周りの機能を中心に実装。

---

必要であれば各機能ごとの使用例、API 詳細、互換性・マイグレーション手順を追記します。どの部分をより詳細に書き起こしましょうか？