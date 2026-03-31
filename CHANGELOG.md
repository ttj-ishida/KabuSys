# CHANGELOG

すべての重要な変更は Keep a Changelog 規約に従って記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース

### 追加 (Added)
- パッケージ初版を公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本パッケージ構成
  - src/kabusys/__init__.py にて公開モジュールを定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env/.env.local の自動ロード実装（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応した .env パーサ実装。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / データベース / 監視 / システム設定を環境変数から取得するプロパティを実装。
    - 必須変数未設定時は明示的な ValueError を送出する _require を実装。
    - KABUSYS_ENV, LOG_LEVEL のバリデーションを実装（許容値に対するエラー報告）。

- AI（LLM）関連機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数上限）を実装。
    - JSON Mode を利用した厳密なレスポンス検証とフォールバック（前後余剰テキストから JSON 部分を抽出）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーションで未知コードや非数値を無視、スコアを ±1.0 にクリップ。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api の patch を想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出（マクロキーワード群）、OpenAI 呼び出し（gpt-4o-mini）とリトライ/フェイルセーフ（API失敗時macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止の設計（date 未満のデータのみ使用、datetime.today() を参照しない）。

- データプラットフォーム機能
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジック（market_calendar テーブルの夜間更新ジョブ、営業日判定・前後営業日検索・期間内営業日取得・SQ判定）を実装。
    - DB が不完全な場合の曜日ベース フォールバックや最大探索日数上限を設定して安全に動作する設計。
    - calendar_update_job により J-Quants からの差分取得と冪等保存をサポート（バックフィル・健全性チェック実装）。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプライン用データクラス ETLResult を実装（取得件数・保存件数・品質問題・エラー集約）。
    - 差分取得・backfill・品質チェック考慮の設計を反映（jquants_client, quality モジュールを活用）。

  - src/kabusys/data/__init__.py にてサブモジュールを整備（ETLResult を再エクスポート）。

- リサーチ（研究）機能
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等の定量ファクター計算を実装（prices_daily / raw_financials のみ参照、外部発注APIへはアクセスしない）。
    - calc_momentum, calc_volatility, calc_value を提供。各関数は (date, code) をキーとする dict リストを返す。
    - 200日移動平均やATRなどのデータ不足に対する None の取り扱いを定義。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存なしで標準ライブラリ + DuckDB SQL による実装。

- 汎用ユーティリティ / 設計点
  - DuckDB を主要な分析用 DB として使用する設計を採用。
  - DB 書き込みは冪等性を意識し BEGIN/DELETE/INSERT/COMMIT または executemany を用いて実装。
  - ルックアヘッドバイアス防止のため日付参照を外部から与える設計（関数は target_date を引数として受け取る）。
  - OpenAI API 呼び出し・失敗処理についてはログ出力とフェイルセーフ（スコア0やスキップ）で堅牢化。

### 変更 (Changed)
- 初回リリースのため過去履歴なし。

### 修正 (Fixed)
- 初回リリースのため過去履歴なし。

### 除外（Deprecated / Removed）
- 該当なし

### セキュリティ（Security）
- OpenAI API キー等の機密情報は環境変数経由で取得。必須変数未設定時は例外により明示的に通知。

### 注意事項（Known limitations / Notes）
- OpenAI 利用
  - 全ての LLM 呼び出しは OpenAI の API キー（OPENAI_API_KEY）が必要。api_key を明示的に渡すことも可能。
  - LLM レスポンスの形式に依存するため、モデル・API の仕様変更があるとパースに影響する可能性がある。

- ニュース NLP
  - 出力は厳密な JSON を期待するが、前後余剰テキストを含むケースに対する簡易抽出ロジックを備える（稀なケースではスキップする）。
  - スコアは ±1.0 にクリップされる。

- ファクター計算
  - PBR / 配当利回り等は現状未実装（calc_value の注記参照）。
  - horizons は最大252営業日の制約（安全上の制限）。

- データベース互換性
  - DuckDB のバージョン差異（例: executemany の空リスト扱い、リスト型バインドの挙動）を考慮した実装を行っているが、利用する DuckDB バージョンにより微調整が必要な場合がある。

- テスト
  - OpenAI 呼び出し関数はモック差し替えを想定しており、ユニットテストの容易化を意識した設計。

---

フィードバックや誤りの指摘、追加したい機能があれば Issue を作成してください。