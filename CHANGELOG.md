# Changelog

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠です。  
このファイルはコードベースの実装内容・設計方針から推測して作成しています。

現在のパッケージバージョン: 0.1.0

## [Unreleased]

### Known issues
- src/kabusys/data/pipeline.py 内の _get_max_date 関数の末尾に不自然なトークン（`return date.fro`）が残っています。実装の途中/タイプミスと見られ、修正が必要です。
- 一部のモジュールで外部 API（OpenAI / J-Quants）呼び出し失敗時にフェイルセーフで 0 を返す設計ですが、呼び出し結果を通知する運用側の仕組み（リトライ通知や永続的失敗のアラート）がまだ限定的です。

---

## [0.1.0] - 2026-04-01
初回リリース（推測）。以下の主要機能・実装を含みます。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン定義 __version__ = "0.1.0" を追加。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定・読み込み機能（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサーを実装。export 形式、クォート内のバックスラッシュエスケープ処理、インラインコメント判定などに対応。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得用の _require() と、アプリケーション設定をまとめた Settings クラスを提供。
  - 設定には J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル判定などが含まれる（妥当性チェックを実施）。

- AI 周り（kabusys.ai）
  - ニュースセンチメント解析（news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI の gpt-4o-mini（JSON Mode）へ送信しスコアリング。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数のトリム制御を実装。
    - レスポンスのバリデーションと ±1.0 でのクリップ、失敗時のフェイルセーフ（スキップ）を実装。
    - DuckDB 互換性のため executemany の空リスト回避などの実装上の工夫あり。
    - 時間ウィンドウ計算 calc_news_window を提供（JST 基準の前日 15:00 ～ 当日 08:30 の UTC 変換）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily と raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しはリトライ戦略（指数バックオフ、5xx と接続系をリトライ対象）を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアスを防ぐため内部で date.today()/datetime.today() を参照しない設計（target_date ベースで処理）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルの取得・更新ロジック、営業日判定 is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB データ優先、未登録日は曜日ベース（週末を非営業日扱い）でフォールバックする整合的なロジック。
    - 夜間ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存、バックフィルと健全性チェック含む）。

  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスにより ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分更新、バックフィル、品質チェックの設計に関する方針を実装で反映（jquants_client 経由で保存、品質チェックは問題検出を継続収集）。

- 研究 / ファクター（kabusys.research）
  - factor_research
    - Momentum、Value、Volatility（ATR）、Liquidity などの定量ファクター計算を実装。
    - calc_momentum, calc_value, calc_volatility を提供。いずれも DuckDB に対する SQL 主導の実装で外部 API 呼び出しは無し。
    - 200 日移動平均や ATR の計算はデータ不足時に None を返すなど堅牢化。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（calc_ic）、rank、factor_summary 等の統計解析ユーティリティを提供。
    - Spearman 的ランク相関の実装（ties の平均ランク扱い）や基本統計量計算など。

- DuckDB 互換性・堅牢化
  - executemany の空リスト回避、NULL 値やデータ不足時のログ出力とフォールバック、日付型の安全な変換ユーティリティ等、DuckDB の実装差やデータ欠損に配慮した実装。

### Changed
- （初回リリースにつき過去変更履歴はなし。実装上の設計決定をドキュメント化）
  - 各 AI モジュール・ETL・calendar で「ルックアヘッドバイアス防止」の設計方針を明記。
  - OpenAI 呼び出し周りは別モジュール間で _call_openai_api を共有しない方針（モジュール結合を抑制）。

### Fixed
- （初回リリースにつき過去修正履歴はなし）

### Removed
- なし

### Security
- OpenAI API キー・各種秘密情報は環境変数経由で取得。Settings クラスにて必須チェックを実装（未設定時は ValueError を発生させる）。

---

注記・運用上の補足
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など
- OpenAI / J-Quants との連携は実稼働環境では API キー・ネットワーク制約・レートリミット・コストに注意してください。実行時のログや Slack 通知等を別途運用で整備することを推奨します。
- 一部未完成/要修正箇所（pipeline._get_max_date の末尾など）は次期リリースで修正することを推奨します。

もし想定リリース日や追加の変更点（例えばバグ修正や機能追加）を指定いただければ、Unreleased 部分に追記して更新案を作成します。