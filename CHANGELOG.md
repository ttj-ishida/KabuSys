# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys。公開モジュール: data, strategy, execution, monitoring（パッケージAPIのエントリポイントを確立）。
  - バージョン: 0.1.0 を設定。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは `export KEY=val` 形式、クォート付き値、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス等の設定アクセサを公開（必須変数は未設定時に ValueError を送出）。
  - デフォルトの DB パス（DuckDB / SQLite）やログレベル・環境モード検証を実装。

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄ごとのセンチメント(ai_score)を算出し ai_scores テーブルへ保存する処理を実装。
    - チャンク処理（デフォルト20銘柄/チャンク）、1銘柄あたりの記事・文字数制限（記事数/文字数トリミング）を実装。
    - API 呼び出しは 429・ネットワーク・タイムアウト・5xx を対象に指数バックオフでリトライ。レスポンス検証（JSON 抽出・キー/型チェック・スコア数値変換）を実装。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30 → UTC 変換）と、ルックアヘッドバイアス防止方針を適用。
    - 部分失敗時にも既存スコアを保護するため、書込み前に対象コードのみ DELETE → INSERT する冪等保存ロジックを採用。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200日移動平均乖離とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - マクロキーワードで raw_news を抽出して OpenAI にスコアを依頼（gpt-4o-mini、JSON mode）。API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - DuckDB 上で冪等に market_regime を書き込むトランザクション（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK のハンドリングを実装。

### 変更（設計・安全性）
- ルックアヘッドバイアス防止
  - AI モジュール / リサーチモジュールで datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える設計を徹底。
  - DB クエリは target_date より前（排他）や LEAD/LAG を適切に使うことで将来データの参照を防止。

- OpenAI 呼び出しと堅牢性
  - gpt-4o-mini を想定した JSON Mode の利用を前提に、レスポンスの JSON 抽出と厳密なバリデーションを実装。
  - RateLimit、接続エラー、タイムアウト、5xx の場合は指数バックオフでリトライ。その他のエラーやパース失敗はログ出力の上で安全にフォールバックする挙動。

- DuckDB トランザクションと部分書き換え
  - ai_scores / market_regime 等の書き込みは、既存データを保護するために対象コードのみを DELETE してから INSERT する方式を採用。DuckDB の executemany の制約に配慮した実装（空リストの扱いに注意）。
  - 書き込み失敗時は ROLLBACK を試行し、ROLLBACK が失敗した場合は警告ログを出力して例外を上位へ伝播。

### 追加（データ関連）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得・保存・品質チェックのための ETLResult データクラスを提供。取得件数・保存件数・品質問題・エラーのサマリを含む。
  - 差分更新のための最小日付やバックフィル日数、カレンダー先読みなどを定義。
  - jquants_client 経由での差分取得・idempotent 保存・品質チェックのフローを想定した設計。

- データユーティリティ / カレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
  - DB にカレンダーデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）を行い、DB がまばらな場合でも一貫性を保つ設計。
  - 夜間バッチ job (calendar_update_job) を実装。J-Quants から差分取得し冪等に保存、バックフィルと健全性チェック（極端な将来日付の検出）を実装。

- データ公開インターフェース
  - kabusys.data.etl で ETLResult を再エクスポートし、外部からの参照を容易に。

### 追加（リサーチ・分析）
- ファクター計算 (kabusys.research.factor_research)
  - Momentum / Volatility / Value / Liquidity 等のファクターを DuckDB 上で計算する関数を実装。
  - calc_momentum, calc_volatility, calc_value を提供。200日移動平均、ATR、出来高指標、PER/ROE 等を算出。
  - データ不足時の None 扱い、範囲スキャンのバッファ設計（営業日換算）等を実装。

- 特徴量探索・統計 (kabusys.research.feature_exploration)
  - 将来リターン計算（calc_forward_returns）、IC（Spearman のランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
  - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。

### 修正（ログ・警告）
- 各モジュールに詳細なログ・警告メッセージを追加し、API 失敗・データ不足・パース失敗などが発生した際に適切に情報が残るようにした。

### 既知の制約・注意点
- OpenAI キー未設定時は score_news / score_regime は ValueError を送出する（api_key 引数または環境変数 OPENAI_API_KEY が必要）。
- news_nlp/regime_detector は JSON mode に依存したレスポンス構造を期待しているため、外部APIやモデル挙動が変わるとパースロジックの更新が必要。
- 一部のパッケージ公開名（strategy, execution, monitoring）は __all__ に含まれるが、このリリースでの実装（コードスニペット）には詳細実装が含まれていない箇所があるため、API の完全整備は以降のリリースで実施予定。

---

今後のリリースでは、エンドツーエンドのテストカバレッジ拡充、strategy/execution/monitoring の具体実装、CI での DuckDB/OpenAI 呼び出しのモック整備、パフォーマンス最適化（大規模データでのクエリチューニング）を予定しています。