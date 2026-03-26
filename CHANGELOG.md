# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
現在のバージョン: 0.1.0 (初回リリース)

## [0.1.0] - 2026-03-26

### 追加 (Added)
- パッケージの初期公開
  - kabusys 主要モジュール群を追加（data, research, ai, monitoring, strategy, execution 等をエクスポート）。
  - パッケージバージョン: 0.1.0

- 環境変数 / 設定管理
  - .env / .env.local ファイルと OS 環境変数から設定をロードする自動読み込み機能を実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - .env パース実装:
    - export プレフィックス対応、クォート／エスケープ処理、行末コメント処理等に対応。
    - .env の読み込み時に OS 側の環境変数を保護する protected 機能、override オプションをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テストなど用）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / ログレベル / 実行環境 (development/paper_trading/live) を取得・バリデーションできる API を追加。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、OpenAI (gpt-4o-mini) を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - チャンク処理（最大20銘柄 / バッチ）・記事トリム（文字数・記事数の上限）・JSON Mode を利用した応答検証を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーションとスコアのクリッピング（±1.0）。
    - API キーの注入（引数）と環境変数経由の解決に対応。テスト用に内部の API 呼び出し関数を差し替え可能（モック可能）。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードによるニュース抽出、OpenAI 呼び出し、閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - ルックアヘッドバイアス回避設計（date 引数ベースで処理し datetime.today()/date.today() を直接参照しない）。

- データ管理（Data）
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）と、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを追加。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した挙動、最大探索日数による安全策を実装。
    - J-Quants クライアントを経由した差分取得・バックフィル・健全性チェックを実装。

  - ETL パイプライン（pipeline.ETLResult, etl での再エクスポート）
    - ETL 実行結果を表す ETLResult データクラスを追加（取得/保存件数、品質問題リスト、エラー要約など）。
    - 差分取得、バックフィル、品質チェック方針に対応する基盤的ユーティリティを実装。

- リサーチ（Research）
  - ファクター計算（research.factor_research）
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR（20日）ベースのボラティリティ、流動性指標、財務由来の PER / ROE 計算を実装。
    - DuckDB SQL を活用した効率的実装（ウィンドウ関数利用）。データ不足時の None 処理やログを整備。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換 util（rank）、ファクター統計サマリー（factor_summary）を実装。
    - ランク計算は同順位の平均ランク対応（丸め処理で ties の検出安定化）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- DuckDB 互換性に関する注意点をコードに反映
  - DuckDB 0.10 系で executemany に空リストを与えるとエラーになる点を考慮し、空リストを渡さないガードを実装（ai/news_nlp, pipeline 等で適用）。
- OpenAI API 呼び出しに対する堅牢化
  - APIError の status_code の有無に依存しない安全な処理（getattr を使用）や 5xx 扱いのリトライ判定を明示。

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用する設計。キー取得失敗時は明示的な ValueError を送出して安全に失敗するようにしている。

### 注意事項 / 設計上の特徴
- ルックアヘッドバイアス回避: 日付依存処理はすべて target_date 引数ベースで実行し、datetime.today()/date.today() などを直接参照しない設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）障害時は可能な範囲で処理を継続・フォールバック（例: macro_sentiment=0.0、失敗チャンクはスキップ）する方針。
- テストしやすさ: OpenAI 呼び出し箇所は内部関数として抽象化しており、unittest.mock.patch 等で差し替え可能。
- DB 書き込みは冪等性とトランザクション（BEGIN/COMMIT/ROLLBACK）を意識して実装。

---

今後のリリースでは、監視・戦略・実行周りの具体的な注文ロジックやモニタリング統合、CLI / システム起動フロー、さらに詳細な品質チェックルールやメトリクス出力を追加予定です。