# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリースはセマンティックバージョニングを採用します。

なお、本 CHANGELOG はリポジトリ内のソースコード内容から推測して作成した初回リリースの要約です。

## [Unreleased]

## [0.1.0] - 2026-04-01

最初の公開リリース。日本株自動売買システムのコア機能群を実装・公開します。主な追加内容は以下のとおりです。

### 追加
- パッケージ基底
  - kabusys パッケージの初期化（__version__ = 0.1.0）と主要サブパッケージのエクスポート設定（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - .env ファイルパーサーにおける詳細対応：
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント（#）の取り扱い
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時等に有効）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル検証など多数のプロパティ）。
    - 必須環境変数未設定時は明確な ValueError を送出する _require() 実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装（許容値のチェック、誤値で例外）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメント・スコアを取得。
    - バッチ処理（最大20銘柄/チャンク）、銘柄あたりの記事数・文字数のトリム制御。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検証、スコアのクリップ）。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）を実装。
    - calc_news_window(): JST 時刻ウィンドウ（前日15:00〜当日08:30）を UTC naive datetime で計算。
    - フェイルセーフ方針: API/パース失敗時は当該チャンクをスキップし、処理継続。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算、raw_news からマクロキーワードで記事タイトルを抽出し OpenAI で macro_sentiment を評価。
    - OpenAI 呼び出しのリトライ・エラー処理（429/接続/タイムアウト/5xx の扱い）、API失敗時は macro_sentiment=0 のフォールバック。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため、内部で date.today() 等を参照しない設計（target_date 指定必須）。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M の連続レコードベース）、200日移動平均乖離、ATR（20日）、流動性指標（20日平均出来高・売買代金）等を DuckDB 上の SQL で計算する関数を実装。
    - raw_financials から PER/ROE を取得してバリューファクターを計算。
    - 設計方針として外部 API に依存せず prices_daily / raw_financials のみを参照。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定日から各ホライズン（デフォルト [1,5,21]）の将来終値に基づくリターンを計算。
    - IC（calc_ic）: スピアマンランク相関による情報係数を計算（同順位の平均ランク処理対応）。
    - 統計サマリー（factor_summary）とランク変換ユーティリティ（rank）。
    - 標準ライブラリのみでの実装（pandas 等に依存しない）。

- Data（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を元に営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末を休日扱い）。
    - calendar_update_job(): J-Quants から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックあり。
  - ETL パイプライン（pipeline）
    - ETL の概念実装と ETLResult データクラスを追加（取得数・保存数・品質問題リスト・エラーリストを含む）。
    - 差分取得・バックフィルの方針、品質チェック（quality モジュール）との連携設計を反映。
  - etl モジュールで ETLResult を再エクスポート。

- 監視 / 設定に関する細かい実装
  - Settings に監視用 PID ファイルパス、CPU/Memory/Disk の閾値が追加され、デフォルト値が設定されている。

### 変更
- 初回リリースのため、API 設計・実装の最初の安定版を確立。
- OpenAI クライアント呼び出しは各モジュールで独立実装し、テスト時に差し替えやすいように _call_openai_api を内部関数として定義。モジュール間で private 関数を共有しない方針を採用。

### 修正
- （初回リリースのため過去の修正履歴は無し。コード中に多数のログ出力・例外処理・フェイルセーフを実装しており、運用中の安定性確保を重視。）

### 既知の制限・注意点
- OpenAI API キー（OPENAI_API_KEY）や J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）、kabu ステーションのパスワード（KABU_API_PASSWORD）、Slack トークン等は必須。Settings の必須項目が未設定の場合は ValueError を送出します。
- jquants_client（J-Quants API 用クライアント）や quality モジュールの具体実装は本 CHANGELOG 作成時点のソースに依存します（存在する前提でコードから呼び出し）。
- DuckDB を前提とした SQL 実装になっているため、別のデータストアを使う場合は移植が必要。
- AI モジュールは JSON Mode を期待するプロンプトとレスポンス検証を行うが、LLM の応答変化により追加の堅牢化が必要になる可能性があります。
- ETL / calendar_update_job 等は外部 API エラーやデータ不整合時に 0 を返すなどフェイルセーフだが、運用者側でログ監視・アラート設定が必要です。

### セキュリティ
- 環境変数ベースでの機密情報管理を前提としています。.env ファイルの取り扱いに注意してください（リポジトリへコミットしないこと）。

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジック・発注実装の追加。
- テストスイートの拡充（ユニット・統合テスト、OpenAI 呼び出しのモック）。
- レスポンスパースやプロンプトへの耐性強化、AI モジュールの評価指標追加。
- ドキュメント（使用法・運用ガイド・運用時のチェックリスト）の充実。

（注）本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれらを優先してください。