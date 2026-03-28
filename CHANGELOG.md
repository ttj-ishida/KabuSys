# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買プラットフォームのコアライブラリを提供します。主な機能・モジュールは以下の通りです。

### 追加 (Added)
- 基本パッケージ
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開 API を __all__ で定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロードを実現。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - 無効行（空行・コメント行・キーなし行）を無視。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - 環境変数取得のユーティリティ _require と Settings クラスを実装し、必須設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* など）や既定値（KABU_API_BASE_URL、データベースパス等）、値検証（KABUSYS_ENV, LOG_LEVEL の列挙チェック）を提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini）へバッチで投げてセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（デフォルト 20 銘柄 / チャンク）と 1 銘柄あたりの最大記事数・最大文字数でトークン膨張を抑制。
    - JSON Mode 応答の堅牢なバリデーション（余計な前後テキストの修復、results 配列の検証、未知コードの無視、スコアの数値化・クリップ）。
    - リトライ方針: 429・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフ。
    - DuckDB 向けの書き込み戦略（部分失敗時に既存スコアを消さないため、対象コードに限定した DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、ma200_ratio 計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを行う。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 として継続。
    - OpenAI 呼び出し用の専用関数を持ち、news_nlp と共有しない実装でモジュール結合を避ける。
    - リトライ・バックオフ、5xx と非5xx の扱い分離など堅牢性を強化。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを想定した market_calendar テーブル管理と夜間差分更新ジョブ calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用し、DB 登録ありの場合は DB 値優先で一貫性を保つ。
    - 最大探索日数の制限や健全性チェック（将来日付の異常検出）など安全策を導入。
    - jquants_client を介した取得・保存処理の呼び出しに対応。

  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した ETL の設計方針を実装（詳細ロジックのためのユーティリティ群）。
    - テーブル存在チェック、テーブル最終日取得等のユーティリティ実装。
    - backfill_days による API 後出し修正の吸収や、品質チェック結果を集約して呼び出し元が判断できる形（errors / quality_issues）を提供。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（約1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL / Python で計算する関数を追加。
    - データ不足時の None 扱い、返却形式は (date, code) を含む dict のリスト。
    - 実行は prices_daily / raw_financials のみ参照し、本番口座・発注 API にアクセスしない設計。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、カラム統計サマリ（factor_summary）を実装。
    - スピアマンランク相関の計算、同順位の平均ランク処理、最小データ点数チェックなどを提供。
    - pandas 等の外部依存を持たず純標準ライブラリで実装。

### 修正 / 設計上の注意点 (Changed / Notes)
- ルックアヘッドバイアス防止
  - ai モジュールおよびリサーチ系の関数は datetime.today() / date.today() を直接参照しない設計。全て target_date を明示的に受け取ることでバックテストでのルックアヘッドを防止。

- DuckDB 互換性
  - DuckDB 0.10 の executemany の空リスト問題を考慮し、executemany を呼ぶ前にパラメータリストが空でないことをチェック。
  - SQL 内での日付取り扱い・型変換に注意したユーティリティを追加。

- API 呼び出しの堅牢化
  - OpenAI / 外部 API 呼び出し部分でのリトライ（指数バックオフ）、5xx とその他エラーの扱い差別化、パース失敗時のフォールバック（スコア 0.0）を実装。
  - レスポンス JSON の前後余計テキストを許容する耐性を追加。

- テスト支援
  - OpenAI 呼び出しラッパー関数（_kabusys.ai.*._call_openai_api）を明示的に切り出し、unittest.mock.patch による差し替えを想定した実装にしている。

### 修正 (Fixed)
- 特になし（初回リリース）

### 削除 (Removed)
- 特になし（初回リリース）

### セキュリティ (Security)
- セキュリティ関連の既知問題は報告されていません。環境変数に API キー等のシークレットを保持する設計のため、.env ファイルの取り扱いとアクセス権限に注意してください。

---

注記:
- 本リリースでは各機能のコア実装を中心に提供しています。今後のリリースで以下を予定しています（例）:
  - より詳細な品質チェックルールの実装拡張（quality モジュール強化）
  - jquants_client / kabu ステーション連携の詳細実装例・ユーティリティ追加
  - テストカバレッジの拡充と CI ワークフロー整備

貢献・バグ報告・改善提案は issue / プルリクエストで歓迎します。