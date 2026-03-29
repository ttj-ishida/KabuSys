Keep a Changelog
=================
すべての重要な変更点をこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」の仕様に準拠しています。

フォーマット
-----------
各リリースは以下のセクションで構成されています: Added, Changed, Fixed, Removed, Security, Breaking Changes。  
日付はリリース日を表します。

[Unreleased]
------------

- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local からの自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - export KEY=val 形式やクォート/エスケープ、インラインコメント対応のパーサ実装
  - 読み込み上書きルール（OS 環境変数を保護する protected set）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定取得用の _require と Settings クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
  - DB パス設定: DUCKDB_PATH / SQLITE_PATH、環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証
- AI 関連モジュールを追加（src/kabusys/ai）
  - news_nlp.score_news: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む
    - JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を提供
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事数・文字数制限）
    - JSON Mode を利用したレスポンス検証、429/ネットワーク/5xx に対する指数バックオフによるリトライ
    - API 失敗時のフェイルセーフ（スコア未取得はスキップ）
    - テスト用に _call_openai_api をパッチ差し替え可能
  - regime_detector.score_regime: ETF(1321) の 200 日 MA 乖離とマクロ記事の LLM センチメントを合成して市場レジーム（bull/neutral/bear）を作成
    - MA とマクロ重み付け（70%/30%）、スコア合成とクリップ、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - LLM 呼び出しに対するリトライおよびフェイルセーフ（失敗時 macro_sentiment=0.0）
    - ルックアヘッドバイアス防止設計（date パラメータを利用、date.today() を直接参照しない）
- Research モジュールを追加（src/kabusys/research）
  - factor_research: モメンタム、バリュー、ボラティリティ等の定量ファクター計算関数を提供
    - calc_momentum, calc_value, calc_volatility を実装（DuckDB SQL を利用）
    - Z スコア正規化ユーティリティを kabusys.data.stats から利用可能にエクスポート
  - feature_exploration: 将来リターン計算、IC（スピアマン順位相関）、ランク変換、統計サマリー等を提供
    - calc_forward_returns（複数ホライズン対応）、calc_ic、rank、factor_summary を実装
    - 外部ライブラリ非依存（標準ライブラリのみ）
- Data モジュールを追加（src/kabusys/data）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - market_calendar が未取得の場合は曜日ベースのフォールバック
    - 最大探索範囲制限、バックフィル、健全性チェック等を実装
    - calendar_update_job により J-Quants から差分取得し保存する処理を提供
  - pipeline / etl: ETL パイプラインの基本インターフェース（ETLResult データクラス）を実装
    - 差分取得、バックフィル、品質チェックの枠組みを設計（jquants_client、quality モジュールに依存）
    - ETLResult に to_dict 等のユーティリティを提供
  - etl を介して ETLResult を公開（src/kabusys/data/etl.py）
- データベースは DuckDB を前提に実装。主要テーブル名（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials）を参照する設計

Changed
- （初版のためなし）

Fixed
- （初版のためなし）

Removed
- （初版のためなし）

Security
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。キーは明示的に必須チェックを実施。

Breaking Changes
- （初版のため Breaking Changes はありませんが、次項の注意点を参照してください）

注意・移行ガイド
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID のいずれかは Settings により必須と扱われます。リリース後に実行する前に .env を準備してください（.env.example を参照）。
- 自動 .env ロード:
  - パッケージはインポート時にプロジェクトルートを探索して .env と .env.local を自動読み込みします。テストや外部プロセスで自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマ期待値:
  - 多くの関数は特定のテーブル・カラム構成（例: prices_daily に date, code, close 等、raw_news に id, datetime, title, content 等）を前提としています。既存データベースを接続する前にスキーマ互換性をご確認ください。
- ルックアヘッドバイアス回避:
  - 多くの処理（news_nlp, regime_detector, research）で datetime.today() や date.today() を直接参照しない設計にしており、target_date を必ず指定して使用してください。
- テストのしやすさ:
  - OpenAI 呼び出しはモジュール毎に _call_openai_api を定義しており、unittest.mock.patch で差し替え可能です。
- 部分書き込みの保護:
  - ai_scores / market_regime などの書き込みは部分失敗時に既存データを不必要に消さないよう、コードで上書き範囲を限定して DELETE → INSERT を行います。

既知の制限・今後の改善候補
- OpenAI モデルと JSON Mode を前提としているため、将来の SDK 変更に伴う調整が必要になる可能性があります（エラーハンドリングや status_code の扱いは互換性を考慮して実装）。
- DuckDB バインドの互換性（executemany の空リスト禁止など）に合わせた実装を行っていますが、異なる DuckDB バージョンでの追加確認が必要です。
- news_nlp のエラーハンドリングはフェイルセーフに徹しており、API 連続失敗時は該当チャンクをスキップします。運用でリトライ戦略やアラート強化が必要になる場合があります。

開発者向けメモ
- モジュール公開 API の一覧（主要な関数/クラス）
  - kabusys.config.settings (Settings)
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / rank / factor_summary
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
  - kabusys.data.ETLResult (via kabusys.data.etl)

お問い合わせ
- バグ報告、フィードバック、機能要求はリポジトリの Issue へお願いします。