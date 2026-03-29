# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog の形式に準拠しています。

全般ルール: 重要な機能追加 / 変更 / バグ修正を記載し、リリース単位で整理します。

## [0.1.0] - 2026-03-29

初回公開リリース — 日本株自動売買システム "KabuSys" の基礎モジュール群を実装・公開しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイント src/kabusys/__init__.py を追加。バージョン情報（0.1.0）および公開サブパッケージ(data, strategy, execution, monitoring) を定義。

- 設定 / 環境管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いを考慮）。
    - 自動ロードの無効化環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 環境変数の必須チェック用 _require と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル等のプロパティを公開。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の許容値チェック。
    - OS 環境変数を保護する protected 上書き制御（.env.local の override 挙動）。

- AI 関連
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に JSON モードで一括送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）。
    - バッチ処理（最大銘柄数: 20）・記事トリム（最大記事数/文字数）・API の再試行（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON パースの復元処理、results リスト検証、未知コードの無視、数値チェック）。
    - DuckDB 互換性のための安全な書き込み処理（部分書き換え戦略: 対象コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - src/kabusys/ai/regime_detector.py を追加。
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - ma200_ratio の計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - マクロキーワードに基づく記事抽出、OpenAI 呼び出しと再試行、API 失敗時は macro_sentiment = 0.0 でフェイルセーフに継続。
    - API 呼び出しは news_nlp の実装と独立して実装しモジュール結合を避ける設計。

- データ基盤
  - src/kabusys/data/calendar_management.py を追加。
    - JPX マーケットカレンダーの管理（market_calendar テーブル想定）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - 夜間バッチ更新 job (calendar_update_job): J-Quants から差分取得、バックフィル、健全性チェック、冪等保存。
    - market_calendar がない場合の曜日ベースのフォールバック実装（堅牢性重視）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py を追加。
    - ETL パイプライン設計方針の実装スケルトン。
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - DuckDB 用のユーティリティ関数（テーブル存在確認・最大日付取得等）を実装。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- リサーチ / ファクター
  - src/kabusys/research/factor_research.py を追加。
    - ファクター計算関数: calc_momentum（1M/3M/6M リターン、200日MA乖離）、calc_volatility（20日ATR, 相対ATR, 平均売買代金, 出来高比率）、calc_value（PER, ROE）。
    - DuckDB を用いた SQL ベース計算を採用し、外部 API への依存なしで再現可能に設計。
    - データ不足時の None 返しなど安全処理。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）。
    - 情報係数（IC） calc_ic（スピアマンのランク相関）、rank、統計サマリー factor_summary。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。
  - src/kabusys/research/__init__.py を追加して主要 API を再エクスポート（zscore_normalize を data.stats から参照）。

- テスト / 開発支援
  - OpenAI 呼び出し箇所に対してパッチしやすい設計を行いユニットテストでの差し替えを容易化。

### 変更 (Changed)
- 初回リリースのため変更履歴なし（新規追加が主体）。

### 修正 (Fixed)
- 初回リリースのため修正履歴なし。

### 既知の制限・設計上の注意点 (Known / Notes)
- news_nlp の出力では厳密な JSON を想定しているが、稀に前後に余分なテキストが混入するケースを考慮して最外の {} を抽出する復元ロジックを実装。とはいえモデル出力の不定性に依存するため完全な保証はない点に注意してください。
- calc_value では現時点で PBR や配当利回りは未実装。
- DuckDB のバージョン差異（例: executemany に空リスト不可）を回避するためのワークアラウンドを導入しています。運用時は使用する DuckDB バージョンの互換性確認を推奨します。
- jquants_client 等の外部クライアントモジュールは参照されているものの、このリリースの範囲での実装詳細は別モジュール（data.jquants_client）に委ねられています。実運用前に実際のクライアント実装と接続設定を行ってください。
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で指定する必要があります。未設定時は ValueError を送出します。
- .env の自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

### 必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能利用時）
- さらに DB パス等は DUCKDB_PATH / SQLITE_PATH でカスタマイズ可能

---

今後予定（例）
- strategy / execution / monitoring モジュールの機能実装（発注ロジック、ポジション管理、監視アラート等）。
- テストカバレッジ拡充と CI 統合。
- モデル出力の堅牢化・プロンプト改善、OpenAI モデル切替の抽象化。

------------------------------------------------------------
（本 CHANGELOG はコードの現状から推測して作成しています。実際の変更履歴やリリースノートは開発チームの記録を優先してください。）