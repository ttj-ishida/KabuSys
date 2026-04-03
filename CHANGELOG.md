CHANGELOG
=========
すべての重要な変更点をここに記録します。形式は「Keep a Changelog」に準拠しています。  
このファイルはプロジェクトのリリース履歴の要約であり、API・設計上の重要な振る舞いやフェイルセーフ、主な追加機能を含みます。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-03
-------------------
初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
- パッケージ基盤
  - kabusys パッケージ初版を追加。__version__ = 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みするユーティリティを追加。
  - プロジェクトルート検出（.git または pyproject.toml）により、CWD に依存しない自動 .env ロード。
  - .env/.env.local の読み込み優先度処理を実装（.env.local が .env を上書き、既存 OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env 行パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティで取得・バリデーション。
  - 必須環境変数未設定時に明確なエラーを投げる _require 実装。

- データ層（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックのための ETLResult データクラスを公開。
    - 差分取得・バックフィル・品質チェックの設計を実装（J-Quants クライアント呼び出しを想定）。
    - DuckDB を前提としたテーブル存在確認や最大日付取得ユーティリティを実装（ETL 用）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを活用した営業日判定ロジックを実装（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - 夜間バッチ job: calendar_update_job により J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェック含む）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR(20)、出来高/売買代金関連指標、ボラティリティ・流動性指標、財務に基づく PER/ROE を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を主体に実装し、営業日ベースでのウィンドウ処理を考慮。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリで実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に、ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装（score_news）。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供（calc_news_window）。
    - バッチサイズ、文字数上限、記事数上限、JSON Mode を用いた厳密なレスポンス検証、スコアの ±1.0 クリップ、最大20銘柄/チャンク処理等を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーションと部分書き込み（成功したコードのみ DELETE→INSERT）により部分失敗時のデータ保護を実施。
    - テスト容易性のため、OpenAI 呼び出し点を _call_openai_api として抽象化（テストで差し替え可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（ウエイト 70%）とマクロニュースの LLM センチメント（ウエイト 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み（score_regime）。
    - マクロニュースはニュース NLP のウィンドウ集約ユーティリティを再利用し、OpenAI を別実装（モジュール結合回避）で呼び出す。
    - API エラー時のフェイルセーフ（macro_sentiment を 0.0 にフォールバック）やリトライロジック、スコアのクリップ、閾値判定等を実装。
    - 外部依存（OpenAI API キー）は引数注入可能（api_key）でテスト容易性を確保。

Changed
- 設計上の方針を明確化
  - すべての「当日参照」を行う処理で datetime.today()/date.today() に依存しない実装方針を採用（ルックアヘッドバイアス防止）。各関数は target_date 引数を取り、必要なウィンドウはそこから算出。
  - DuckDB を前提とした SQL ベースの集計を多用し、外部ネットワークアクセス（取引API等）はリサーチ系関数では行わない設計に統一。

Fixed
- データ安全性 / トランザクション
  - DuckDB への書き込み時に BEGIN / DELETE / INSERT / COMMIT を用いた冪等化を導入。例外発生時に ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告ログを出力する実装を適用。

- レスポンスパースと異常対応
  - OpenAI JSON レスポンスが前後に余計なテキストを含むケースに対し、中括弧ペア抽出で復元を試みる等、堅牢性を向上。

Security
- 環境変数管理で OS 環境を優先し、不用意な .env 上書きを防ぐ保護処理を実装。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化で CI/テスト環境での秘密情報漏洩リスクを軽減。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定し JSON Mode（response_format={"type": "json_object"}）での利用を前提としているが、API 変化に備えたエラー処理を備えている。
- News/NLP と Regime Detector はそれぞれ独立して OpenAI 呼び出し実装（_call_openai_api）を持ち、モジュール間でプライベート関数を共有しない設計。
- 設定（Settings）はログレベルと環境（development/paper_trading/live）の値検証を行い、不正値時は ValueError を送出する。
- ETL/カレンダー更新ジョブは J-Quants クライアント（kabusys.data.jquants_client）との連携を想定しており、fetch/save の失敗は例外ロギング後に安全に 0 を返す設計。

今後の予定（例示）
- strategy / execution / monitoring モジュールの詳細実装とテスト整備。
- より詳細なドキュメント（API リファレンス、運用手順、テストケース）の追加。
- モデル選定やプロンプト改良に基づく AI スコアリングのチューニング。

------------------------------------
注: 本 CHANGELOG はリポジトリ内のソースコード（関数名・定数・docstring 等）から推測して作成しています。実際のリリースノートは運用時に合わせて調整してください。