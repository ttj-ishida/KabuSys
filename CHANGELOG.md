# CHANGELOG

すべての変更は "Keep a Changelog" の形式に従っています。  
このプロジェクトはまだ初期リリース段階です。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- 初期リリース。
- パッケージ基盤
  - パッケージバージョン: 0.1.0
  - パッケージ公開インターフェースを定義（kabusys.__all__ に data, strategy, execution, monitoring を公開）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読込機能を実装。
  - .env のパース機能を実装（コメント行、export プレフィックス、シングル／ダブルクォート、エスケープを考慮）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等の設定値を取得する public API を提供。
  - 必須環境変数の存在チェック（未設定時は ValueError を送出）。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を提供（calc_news_window）。
  - バッチ処理（1回あたり最大20銘柄）・記事数/文字数トリム・JSON モード検証・レスポンスバリデーション・スコアクリップを実装。
  - 再試行（429・ネットワークエラー・タイムアウト・5xx）に対する指数バックオフ実装。
  - API 呼び出し箇所にテスト用差し替えフックを用意（_call_openai_api の patch が可能）。
  - score_news(conn, target_date, api_key=None) を公開（書き込み件数を返す）。
- レジーム検出（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する score_regime を実装。
  - マクロ記事フィルタ用キーワード群・最大記事数制限・OpenAI 呼び出し・リトライ/フェイルセーフ（API失敗時は macro_sentiment = 0）を実装。
  - DuckDB への冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
- データ（kabusys.data）
  - カレンダー管理モジュール（calendar_management）を実装。
    - market_calendar テーブルを利用した営業日判定（is_trading_day, is_sq_day）。
    - 前後の営業日探索（next_trading_day, prev_trading_day）、期間内営業日列挙（get_trading_days）。
    - J-Quants からの差分取得を行う夜間バッチジョブ calendar_update_job を実装（バックフィル・健全性チェックあり）。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日）を実装。
  - ETL パイプライン（pipeline）を実装。
    - 差分取得・保存 (jquants_client 経由)・品質チェック（quality モジュール呼び出し）を行う設計。
    - ETLResult データクラスを実装し、ETL 結果の集計・シリアライズ（to_dict）を提供。
- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）：モメンタム・バリュー・ボラティリティ等の計算関数を実装（calc_momentum, calc_value, calc_volatility）。
  - 特徴量探索モジュール（feature_exploration）：将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
  - 標準ライブラリ＋DuckDB のみで動作する実装方針を採用。
- その他ユーティリティ
  - データ変換・正規化ユーティリティ（zscore_normalize）を data.stats 経由で再エクスポート（research パッケージで利用）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する実装。未設定時は ValueError を発生させ、誤用を防止。

### 実装上の注意・設計方針
- ルックアヘッドバイアス対策: 日付参照（score_* / calc_*）は datetime.today()/date.today() を参照せず、引数の target_date に依存する設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は可能な範囲で処理継続し、致命的問題のみ例外伝播。LLM 失敗時は既定値（例: macro_sentiment=0.0）へフォールバック。
- テスト容易性: OpenAI 呼び出し関数にテスト用にパッチ可能な内部関数を用意。
- DuckDB 互換性配慮: executemany の空リスト回避や日付型ハンドリング等を考慮。
- 再試行ロジック: LLM 呼び出しはレート制限・タイムアウト・5xx に対して指数的バックオフでリトライ。

---

今後のリリースでは、以下のような項目を予定しています（例）:
- strategy / execution / monitoring モジュールの実装（自動売買ロジック・発注ラッパー・監視・アラート）。
- テストカバレッジの拡充・CI ワークフロー追加。
- ドキュメント（API リファレンス・運用手順）の整備。