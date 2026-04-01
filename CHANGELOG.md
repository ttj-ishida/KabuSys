# Changelog

All notable changes to this project will be documented in this file.

このファイルは Keep a Changelog の慣例に従って記載しています。  
אנ initial リリース（0.1.0）について、コードベースから推測できる実装内容・仕様・既知の問題点をまとめています。

---

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-01

初期リリース。以下の主要機能群を実装／公開します。実装は主に DuckDB をデータレイヤーとして想定し、J-Quants API および OpenAI（gpt-4o-mini）と連携する ETL / 解析 / AI モジュールを中心に含みます。

### 追加 (Added)

- 基本パッケージ情報
  - パッケージバージョン: 0.1.0
  - パッケージトップでの公開モジュール: data, strategy, execution, monitoring（__init__で __all__ を設定）

- 環境変数 / 設定管理（kabusys.config）
  - .env および .env.local からの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 行パーサ: export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理
  - OS の既存環境変数は protected として上書きされない（override パラメータあり）
  - Settings クラスでアプリケーション設定を公開（必須環境変数は _require() で ValueError を投げる）
    - 必須環境変数（使用関数に依存）例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルトパス: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), PID_FILE_PATH (data/execution.pid)
    - リソース閾値設定: CPU/MEM/DISK の閾値（%）
    - 環境種別検証（development / paper_trading / live）とログレベル検証

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へ送信して銘柄別センチメント（-1.0〜1.0）を生成
    - チャンク処理（最大 20 銘柄 / API 呼び出し）
    - 入力サイズ保護: 1 銘柄あたり最大記事数 10 件、最大文字数 3000 文字でトリム
    - JSON mode を利用し厳密 JSON 出力を期待（レスポンスのバリデーションと復元処理あり）
    - リトライ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ（最大リトライ）
    - 成功データのみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時に既存データを保護）
    - 公開 API: score_news(conn, target_date, api_key=None)
    - ユーティリティ: calc_news_window(target_date)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定
    - OpenAI JSON mode と同様のリトライ／フォールバック設計（API 失敗時は macro_sentiment = 0.0）
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 公開 API: score_regime(conn, target_date, api_key=None)

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None／中立扱い）
    - Value: PER（EPS が無効な場合は None）、ROE（raw_financials から取得）
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - 全て DuckDB 上の SQL で計算し、(date, code) ベースの dict リストを返す
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
    - 将来リターン計算（ホライズンのバリデーションあり、デフォルト [1,5,21]）
    - IC（スピアマンランク相関）計算
    - 基本統計量サマリー
    - ランク付け実装（同順位は平均ランク）

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - calendar_update_job: J-Quants から差分取得して市場カレンダーを冪等的に更新（バックフィル・健全性チェックあり）
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）
    - pipeline での差分取得、保存（jquants_client を通じて idempotent 保存）、品質チェック（quality モジュール）を想定
    - ETLResult は品質問題とエラーの集約をサポート

- ロギング
  - 各モジュールで詳細なログ出力（info / warning / debug）が組み込まれているため運用時のトラブルシュートが容易

### 変更 (Changed)

- 初期リリースのため特別な変更履歴はなし（ベースラインの実装を追加）

### 修正 (Fixed)

- 初期リリースのためなし

### 既知の問題 (Known issues)

- pipeline._get_max_date の実装がファイル中で途切れている（ソース断片: "return date.fro" のような不完全な行が存在）。このままではモジュールのインポート時または関数呼び出し時に SyntaxError / 実行時エラーとなる可能性が高い。リリース前に修正が必要。
- data/__init__.py が空のまま（エクスポートや初期化ロジックが未配置）だが、これは意図的なプレースホルダである可能性あり。運用時に必要な public API が未整理の場合がある。
- __init__.py の __all__ に strategy, execution, monitoring を含めているが、提示コード内にこれらの実装ファイルが含まれていない（別途実装または追加が必要）。
- OpenAI / J-Quants 連携部分は外部 API に依存するため、API キーやネットワーク障害に対する動作はフォールバック（0.0のスコア）で安全側に設計されているが、API 利用制限やレスポンス仕様変更により想定外の結果が返る可能性がある。
- DuckDB の executemany に関するバージョン差異（空リスト不可等）へ対処しているが、実際の DuckDB バージョン依存の微妙な挙動が残る可能性がある。

### セキュリティ (Security)

- セキュリティ関連の修正はなし（ただし API キー等の取り扱いは環境変数経由を推奨）

---

## 移行 / 使用上の注意 (Migration / Usage notes)

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants API 利用時に必要
  - KABU_API_PASSWORD: kabu ステーション API 利用時に必要
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知使用時に必要
  - OPENAI_API_KEY: score_news / score_regime 等の AI 機能を利用する場合に必要
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- デフォルト DB ファイルパスは Settings クラスで定義（必要に応じて環境変数で上書き）
- AI 関連処理はコストとレイテンシが発生するためバッチ処理や運用ポリシーを設計すること

---

Notes:
- 本 CHANGELOG は提示されたソースコードから挙動・設計方針を推測してまとめたものです。実際の挙動や API レスポンス例、追加のモジュールはリポジトリ全体に依存します。必要であれば、抜けている箇所（pipeline._get_max_date の未完了行や欠落モジュール）を特定して修正案を含めたアップデート用の CHANGELOG エントリを作成します。