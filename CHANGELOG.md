Keep a Changelog
=================

このファイルは Keep a Changelog のフォーマットに準拠しています。  
シンタックスはセマンティックバージョニング (SemVer) に従います。

[Unreleased]
------------

- （今後の変更をここに記載します）

[0.1.0] - 2026-04-02
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。
主な追加項目、設計上の方針、既知の制限を以下にまとめます。

Added
- パッケージ基盤
  - パッケージメタ情報: src/kabusys/__init__.py に __version__="0.1.0" と主要サブパッケージの再エクスポートを追加（data, research, ai, ...）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - 強化された .env パーサ:
    - export KEY=... 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント取り扱い等。
  - 環境変数取得ラッパー Settings クラスを提供（各種必須変数チェック、パス展開、型変換、値検証）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - 環境 KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- AI モジュール (src/kabusys/ai/)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄毎に OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - チャンクサイズ、記事数・文字数トリム、JSON mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - レート制限やネットワーク障害・5xx を考慮した指数バックオフ付きリトライ。
    - 部分成功に対応する idempotent な DB 書き込み（DELETE → INSERT、書き込み対象コードを限定）。
    - DuckDB の executemany における空リスト制約を考慮した実装。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照、ma200_ratio の計算はルックアヘッドを防止する設計（target_date 未満のデータのみ使用）。
    - マクロセンチメントは OpenAI をコールし、API 障害時は 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API 呼び出しは内部で独立実装し、テスト用に差し替え可能（モック可）。
- データプラットフォーム / ETL (src/kabusys/data/)
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定・prev/next_trading_day・get_trading_days・is_sq_day を実装。
    - market_calendar 未取得時は曜日（平日）をフォールバックとして利用する堅牢な設計。
    - calendar_update_job: J-Quants からの差分取得と idempotent 保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py、src/kabusys/data/etl.py）
    - ETLResult データクラス（取得件数、保存件数、品質問題、エラー概要の集計）。
    - 差分更新・バックフィル・品質チェックを想定した基本設計（詳細な ETL 実行ロジックは jquants_client / quality に依存）。
    - data.etl で ETLResult を再エクスポート。
  - jquants_client（間接参照）を介したデータ取得/保存の想定インターフェースに対応。
- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M）、200日MA乖離、ATR（20日）、出来高・売買代金系のファクターを DuckDB SQL ベースで計算。
    - データ不足時の None 戻し、営業日に対するスキャンバッファ等の設計。
  - feature_exploration.py
    - 将来リターン（任意ホライズン）の計算（1,5,21 日がデフォルト）、IC（Spearman）計算、ランク変換、ファクターの統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで主要関数を再エクスポート。
- ロギング・ロバストネス
  - 各所に詳細な logger 出力を追加。API 失敗・パース失敗時に警告ログを出力してフェイルセーフにする実装。
  - OpenAI SDK の APIError.status_code 未定義ケースへの耐性を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱い:
  - 自動 .env ロードでは OS 環境変数を保護（.env の上書きを防止）。
  - 必須トークンは Settings で明示的に検証。OpenAI キー等は環境変数または関数引数で注入する想定。
- OpenAI 呼び出しはタイムアウト・リトライ・フェイルセーフを備え、過剰な例外漏洩を抑制。

Known issues / 注意点
- DuckDB との互換性:
  - executemany が空リストを許容しないバージョン（例: DuckDB 0.10 系）への配慮をしているが、実際の環境差異により微調整が必要な場合があります。
- OpenAI JSON Mode の応答形式:
  - response_format={"type": "json_object"} を期待しているが、稀に前後に余計なテキストが混入するため、パーサは最外側の {} を切り出す復元処理を行う。レスポンスの互換性に注意してください。
- ルックアヘッドバイアス防止:
  - 全ての時刻計算・クエリは target_date を明示的に受け取り、内部で date.today()/datetime.today() を直接参照しない設計です。運用時は target_date の指定を正しく行ってください。
- 部分失敗時の振る舞い:
  - AI API 呼び出し失敗時は対象銘柄をスキップして処理を継続する設計です（失敗分は後続で再処理が必要）。ETLResult にエラー情報が蓄積されるため呼び出し元でのハンドリングを推奨します。

Development notes / 設計方針のハイライト
- DB 書き込みはなるべく冪等に（DELETE→INSERT、ON CONFLICT 想定）。
- 外部 API 呼び出しは明確に注入可能（api_key 引数等）にしてテスト容易性を確保。
- 「失敗しても止めない」方針を採用（API 障害はログ記録→フェイルセーフなデフォルトで継続）。
- 可能な限り外部依存を減らし、DuckDB + 標準ライブラリ中心で実装。

Credits
- 実装者が README / DataPlatform.md / StrategyModel.md 等の設計仕様に基づき開発。

Acknowledgements / ライセンス
- ライセンス情報・外部サービス利用条件（OpenAI, J-Quants 等）は別途ドキュメントを参照してください。

（以降のバージョンでは、テストの追加、ETL 実行フローの詳細実装、UI/運用用 CLI、発注実行モジュールの実装・安全性強化などを予定）