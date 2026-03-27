# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニング (MAJOR.MINOR.PATCH) を採用しています。

最新更新: 2026-03-27

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回リリース。自動売買プラットフォームの基本モジュール群を実装。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージ初期版を追加。__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring を定義。

- 設定 / 環境変数ローダー (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env / .env.local の読み込み順序制御（OS 環境変数を保護、.env.local が上書き可能）。
  - 行パーサー実装: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の細かい取り扱い。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 設定取得ラッパー Settings を提供。主な設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証
    - ヘルパープロパティ: is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - news_nlp モジュール: ニュース記事を集約して OpenAI により銘柄単位のセンチメントを算出し ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST)、銘柄毎のテキスト結合とトリム、バッチ送信（最大 20 銘柄/回）。
    - OpenAI JSON Mode 利用、レスポンス検証、スコアクリッピング（±1.0）。
    - レート制限/ネットワーク/5xx に対する指数バックオフとリトライ。API 失敗時は部分スキップして継続。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクションとROLLBACK ハンドリング）。
    - テスト用フック: _call_openai_api を patch 可能に設計。
  - regime_detector モジュール: ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立 1.0 を採用）。
    - マクロ記事抽出（キーワードリスト）→ LLM 評価（gpt-4o-mini、JSON）→ 合成スコア。
    - LLM エラーに対するリトライ戦略とフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラー時の ROLLBACK 保護。
  - ai パッケージ外部 API:
    - score_news(conn, target_date, api_key=None) → ai_scores へ書き込み、戻り値は書き込み銘柄数。
    - score_regime(conn, target_date, api_key=None) → market_regime へ書き込み、戻り値は 1（成功）。

- データプラットフォーム (kabusys.data)
  - calendar_management モジュール:
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 値優先だが不足時は曜日ベースでフォールバック。最大探索日数で無限ループ防止。
    - 夜間バッチ job (calendar_update_job) を実装。J-Quants から差分取得し冪等保存、バックフィルと健全性チェックを実施。
  - pipeline / etl:
    - ETLResult dataclass を追加（ETL 実行結果の集約：取得数・保存数・品質問題・エラーリスト等）。
    - 差分更新、backfill、品質チェックを想定した ETL 基盤設計（jquants_client と quality モジュール連携を前提）。
    - _get_max_date 等のユーティリティを実装。

- 研究用ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials からモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 設計上、外部 API 呼び出しなし、DuckDB SQL を活用した実装。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（スピアマン秩相関 / IC）、rank（平均ランク処理）、factor_summary（基本統計量）を実装。
    - pandas 等に依存しない実装。

### 変更 (Changed)
- 全体設計方針として以下を明確化
  - ルックアヘッドバイアス防止: 各処理で datetime.today()/date.today() を直接参照しない（target_date 引数ベース）。
  - DB 書き込みは冪等性を重視し、トランザクションと個別 DELETE→INSERT のパターンを採用（部分失敗時のデータ保護）。
  - OpenAI API 呼び出しは JSON mode を想定した堅牢なパースとバリデーションを実装。

### 修正 (Fixed)
- API 呼び出し失敗やレスポンス不正時の堅牢性を強化
  - OpenAI からの 5xx / RateLimit / タイムアウト等をリトライ対象とし、非再試行エラーでは安全にフォールバック（0.0 やスキップ）する実装。
  - JSON パース失敗時には本文から最外の {} を抽出して復元するフォールバックロジックを追加（news_nlp）。
  - DuckDB executemany の空リスト制約に配慮して条件分岐を導入（空リスト時は実行しない）。

### ドキュメント / 開発者向け注意点 (Documentation / Notes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - .env.example を参考に .env を作成すること。自動ロードはパッケージが配置されたプロジェクトルートを基に行われる。
- テスト用フック:
  - news_nlp._call_openai_api / regime_detector._call_openai_api を unittest.mock.patch して外部 API 呼び出しを差し替え可能。
- DB スキーマ依存:
  - modules は DuckDB 上の特定テーブル (prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等) を前提とする。適切なスキーマが必要。
- 時刻扱い:
  - news window は UTC naive datetime を使用（JST→UTC の変換済みで DB と比較する設計）。

### 既知の制限 / TODO
- strategy / execution / monitoring の具体的な発注ロジック・モニタリング機能は本バージョンでは未実装（パッケージ構成は用意済み）。
- 一部の財務指標（PBR・配当利回り等）は未実装。
- 外部 API クライアント（jquants_client, quality）が別モジュールとして想定されており、実際の API 実装・接続は別途必要。
- 単体/統合テストは想定済みだが、テストスイートは本リポジトリに含まれていない。

### セキュリティ (Security)
- 環境変数による API キー管理を前提。機密情報は .env ファイル・環境変数で管理すること。

---

以上が本コードベースから推測される初期リリース (0.1.0) の変更履歴です。追加情報や実際のリリース日付・バージョニングポリシーを指定いただければ、更新して反映します。