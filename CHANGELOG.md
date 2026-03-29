Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。
（コードベースの内容から機能・設計意図を推測して記載しています）

Keep a Changelog
================

すべての注記は SemVer に従います。  
このファイルはコードから推測した主要な変更点・リリースノートをまとめたものです。

Unreleased
----------

- 今後の変更点をここに記載します。

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ初期実装
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 複雑な .env の行パース対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメントの取り扱い等）。
  - Settings クラスを提供し、アプリ設定をプロパティとして安全に取得（必須キー未設定時は ValueError）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）、KABUSYS_ENV のバリデーション、LOG_LEVEL のバリデーションなどを実装。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を明示。

- AI 関連機能（src/kabusys/ai/*）
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウの計算（前日15:00 JST ～ 当日08:30 JST の UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたり記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API 呼び出しでのリトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。失敗時は部分スキップして継続するフェイルセーフ設計。
    - DuckDB に対する書き込みは冪等性を考慮（該当 date/code を DELETE → INSERT）。DuckDB executemany の空リスト制約を回避する実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し market_regime テーブルへ保存。
    - マクロニュースの抽出（キーワードベース）と LLM スコア化（gpt-4o-mini, JSON mode）、レスポンスのパース・リトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止のため日付比較は厳格に実装（target_date 未満のみ参照、datetime.today() 等は使用しない）。
    - DB 書き込み時に BEGIN/DELETE/INSERT/COMMIT を用いた冪等処理と ROLLBACK ハンドリングを実装。

- データ基盤（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定・翌営業日・前営業日・期間の営業日取得・SQ日判定等のユーティリティを提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - calendar_update_job を実装し J-Quants API から差分取得 → 保存（バックフィル、健全性チェック、冪等保存）を行う。
    - 検索上限 (_MAX_SEARCH_DAYS) やバックフィル日数、健全性チェック等の安全機構を提供。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを定義し、ETL 実行結果（取得数、保存数、品質チェック結果、エラーメッセージなど）を収集・出力可能に。
    - 差分更新・バックフィル・品質チェック（品質問題は収集して呼び出し側で対応）といった設計方針、DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
    - jquants_client 経由の保存処理と互換性を想定した設計。

- リサーチ / ファクター分析（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER, ROE）等のファクター算出を SQL（DuckDB）中心で実装。
    - データ不足時の None 対応、結果は (date, code) をキーとする dict リストを返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、horizons デフォルト [1,5,21]、ホライズン検証あり）。
    - IC（Spearman の ρ）計算、ランク化ユーティリティ（同順位は平均ランクで扱う）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を避けた標準ライブラリのみの実装方針。

Changed
- N/A（初回リリース想定のため過去変更点はなし）。

Fixed
- N/A（初回リリース想定のため不具合修正履歴はなし）。

Security
- 注意: OpenAI API キーや各種トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*）は環境変数で扱うことを想定。設定ミスは ValueError を発生させる保護を実装。

注記 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須取得（未設定時は例外）。
  - OpenAI API は news_nlp.score_news / regime_detector.score_regime の呼び出し時に api_key 引数を渡すか OPENAI_API_KEY 環境変数を設定する必要あり。
- .env の挙動:
  - プロジェクトルート自動検出（.git or pyproject.toml）を行うため、パッケージ配布後でも CWD に依存しない。
  - .env.local は .env の上書き用に読み込まれる（ただし OS 環境変数は保護される）。
- DuckDB に関する注意:
  - executemany に空リストを渡せない環境（DuckDB 0.10 など）への対処を実装済み。空パラメータ時は書き込みをスキップするロジックあり。
- 日付・タイムゾーン:
  - ニュース窓やリサーチ処理は UTC naive な datetime を使い、JST ↔ UTC の変換を明示している。全体的にルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計が採用されている（ただし calendar_update_job などでは実運用として date.today() を使用）。
- デフォルト値:
  - OpenAI モデルは gpt-4o-mini を想定。
  - リトライ回数、バックオフなどはコード内定数で管理（_MAX_RETRIES 等）。

今後の改善候補（コードから推測）
- news_nlp と regime_detector の OpenAI 呼び出し部分の共通化（現在は意図的にモジュール間で private 関数を共有していない）。
- ai スコアの永続層における部分トランザクションの可視化や監査ログの強化。
- テスト用のモック・フェイク DB/クライアントの整備（既に _call_openai_api はテスト差替えを想定した書き方）。
- より細かいエラーレベル／アラート（Slack 通知等）統合。

（以上）