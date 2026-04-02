Keep a Changelog 準拠の CHANGELOG を以下に記載します。
コードベースの内容から推測して作成しているため、「設計・実装上の方針」「既知の注意点」なども合わせて記載しています。

CHANGELOG.md
===========

すべての重要な変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメント更新や小さな改善を想定（未リリース）。

[0.1.0] - 2026-04-02
--------------------

Added
- 初回公開: KabuSys 0.1.0
  - パッケージ構成（主要モジュールを含む）:
    - kabusys.config: 環境変数・設定管理
      - .env / .env.local 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
      - export 形式、クォート／エスケープ、インラインコメント対応のパーサ実装
      - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
      - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / env/log レベル検証など）
      - 環境変数未設定時に分かりやすいエラーメッセージを返す _require 実装
    - kabusys.ai.news_nlp: ニュースセンチメントスコアリング
      - ニュース収集ウィンドウ計算（JST 基準 -> DB の UTC 比較に対応）
      - 銘柄毎に記事を集約し（件数・文字数制限）、最大 BATCH 単位で OpenAI にバッチ送信
      - JSON Mode を前提としたレスポンス検証（部分パース復元ロジック含む）
      - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ
      - スコアのクリップ（±1.0）、取得成功分のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）
      - テスト容易性のため API 呼び出し箇所を差し替え可能に実装
    - kabusys.ai.regime_detector: 市場レジーム判定
      - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定
      - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成（重み付け: MA 70% / Macro 30%）
      - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
      - OpenAI SDK の例外型（status_code）を安全に扱う実装
    - kabusys.data.calendar_management: マーケットカレンダー管理
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
      - market_calendar が未取得の場合は曜日ベースでフォールバック（週末は非営業日扱い）
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新、バックフィル・健全性チェックあり
    - kabusys.data.pipeline / kabusys.data.etl: ETL パイプライン周り
      - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等を集計）
      - 差分更新・バックフィル・品質チェックを想定した設計
    - kabusys.research: ファクター計算・特徴量探索
      - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials ベース）
      - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
      - 外部依存を極力排し、DuckDB 上で SQL と純 Python による実装
  - DuckDB を想定した SQL 実装により高性能なデータ参照を実現

Changed / Improved
- API 呼び出しまわりの堅牢化
  - OpenAI 呼び出しは専用の内部関数でラップしており、テスト時に差し替え可能
  - JSON パース失敗・不正レスポンスに対してログ出力してフォールバック（例外を投げず継続）
  - レート制限・接続エラー・タイムアウト・5xx を対象に指数バックオフでリトライ
- DB 書き込みは冪等化を重視
  - market_regime / ai_scores 等は対象コードのみを削除してから挿入することで部分失敗時の既存データ保護を実現
  - DuckDB の executemany に対する互換性（空リスト禁止）を考慮したガードを追加
- ルックアヘッドバイアス防止設計
  - datetime.today() / date.today() をスコア算出の内部ロジックで参照しない（target_date パラメータを必須にする実装）
  - prices_daily 等のクエリで target_date 未満条件を明確にして先読みを防止
- 環境設定のバリデーション
  - KABUSYS_ENV と LOG_LEVEL の許容値検査を実装し、不正値は ValueError を発生させる
- ニュース処理の堅牢化
  - 銘柄ごとのトークン肥大対策（記事数・文字数の上限）を実装
  - LLM レスポンスの形式検証・未知コード無視等の防御的処理を導入

Fixed
- JSON モード使用時に前後ノイズが混入するケースへの耐性向上（最外側の {} を抽出してパースを試行）
- OpenAI SDK の APIError の status_code が存在しないケースへの安全対処（getattr を使用）
- DuckDB executemany に空配列を渡すと失敗する点を回避するガード実装
- raw_news の検索やウィンドウ計算で半開区間（[start, end)）を明示してルックアヘッドを防止

Security
- 必須の外部機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は Settings で必須化。
  - 未設定時は明示的な ValueError を発生させ、誤った実行を防止。
- .env の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時に推奨）

Documentation / Tests (設計メモ)
- 多くの API 呼び出し箇所（OpenAI 連携など）は差し替えを想定しており、ユニットテストが容易
- docstring に設計方針・例外動作・フェイルセーフ動作を詳述

Known issues / Notes
- pipeline._get_max_date 関連のコード断片が途中で切れている（ソースの末尾が不完全）。この箇所は実装ミス（typo / 切り落とし）と思われるため、実行前に該当関数の正しい実装を確認・修正してください。
- パッケージの __all__ には "strategy", "execution", "monitoring" が含まれているが、今回の公開コードにはそれらの実装が含まれていません。将来的なモジュール追加／公開の予定を示唆していますが、現行リリースでは未実装です。
- DuckDB のスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）が前提となります。既存 DB スキーマが異なる場合はマイグレーションが必要です。
- OpenAI モデルは gpt-4o-mini を想定したプロンプト設計を行っています。API の仕様変更等があった場合、プロンプトやレスポンス処理を調整する必要があります。

Contributing
- バグ報告・プルリクエスト歓迎。テスト可能性を重視した設計のため、ユニットテスト（特に OpenAI 呼び出しのモック）を同梱してください。

ライセンス
- （コードベースのライセンス情報が提示されていないため、実際の公開時には LICENSE を明示してください）