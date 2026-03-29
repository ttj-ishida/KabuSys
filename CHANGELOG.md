CHANGELOG
=========

すべての変更は「Keep a Changelog」形式で記載しています。  
安定したリリースや重要な変更はバージョンごとにまとめています。

フォーマット詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 基本パッケージ情報:
    - src/kabusys/__init__.py にてバージョン 0.1.0 を設定し、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 環境設定 / ロード機能（src/kabusys/config.py）を実装
  - .env/.env.local ファイルおよび OS 環境変数からの設定読み込みをサポート。
  - プロジェクトルートの自動探索ロジックを実装（.git または pyproject.toml を基準）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサを実装（export 句対応、シングル/ダブルクォート、エスケープ、行内コメント処理）。
  - Settings クラスを提供しアプリケーション設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID の必須チェック。
    - KABUS_API_BASE_URL、DB パスのデフォルト（duckdb / sqlite）、LOG_LEVEL / KABUSYS_ENV のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- AI 関連: ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols テーブルから記事を銘柄別に集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出。
  - タイムウィンドウ計算（JST 基準 -> UTC 変換）を提供する calc_news_window を実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたり記事上限・文字数トリムの実装。
  - JSON Mode を用いた応答検証と堅牢なパースロジック（前後の余計なテキストをトリムして JSON を復元）。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ。
  - スコアを ±1.0 にクリップ。無効レスポンス時はスキップ（例外を投げずフォールバック）。
  - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - ai_scores テーブルへの冪等的な置換（DELETE → INSERT）を実装。部分失敗時に他銘柄データを保護。
- AI 関連: 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して日次レジーム（bull/neutral/bear）を判定。
  - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満限定）、データ不足時は中立 1.0 を返すフェイルセーフ。
  - マクロ記事抽出（キーワードベース）、OpenAI 呼び出しとリトライ、API 失敗時は macro_sentiment=0.0 で継続。
  - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK 処理）。
  - モジュール間の疎結合設計（news_nlp の内部関数を共有しない等）。
- Research（ファクター・特徴量探索）機能（src/kabusys/research/...）
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を実装。
    - 欠損やデータ不足時の None 戻しなどフェイルセーフを実装。
  - feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank（同順位平均ランク）、factor_summary（基本統計量算出）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみでの実装。
  - re-export: src/kabusys/research/__init__.py で主要関数を公開。
- Data プラットフォーム機能（src/kabusys/data/...）
  - calendar_management.py:
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダーがない場合の曜日ベースフォールバック、DB 層優先の一貫したロジックを採用。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、保存処理）。
  - pipeline.py / etl.py:
    - ETLResult データクラス（ETL 結果概要、品質問題・エラー一覧・シリアライズ）を実装し、etl モジュールで再エクスポート。
    - 差分取得、バックフィル戦略、品質チェック統合を想定した ETL の設計（jquants_client / quality モジュールとの連携ポイントを確保）。
  - DB ヘルパー・ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
- いくつかの設計上の方針・実装注意点を明記
  - いずれの分析処理も datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。target_date を外部から与える設計。
  - API 失敗時は例外で停止せずフォールバック／スキップする方針（フェイルセーフ）。
  - DuckDB の executemany に対する互換性対策（空パラメータ回避等）。
  - 外部 API 呼び出しに対するリトライ・バックオフ実装。
  - ロギング（情報・警告・例外）を豊富に組み込み。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API を利用する機能は実行時に OPENAI_API_KEY を必要とする（引数での注入も可）。未設定時は ValueError を送出する。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, 等）が事前に必要。スキーマ整備は別途スクリプト/マイグレーションで提供する想定。
- news_nlp / regime_detector の OpenAI 呼び出しはテスト容易性のため差し替え可能だが、実行環境での API レートやコストに注意。
- 一部の API 呼び出し（jquants_client 等）は外部モジュールに依存しており、実行には該当モジュールの提供・設定が必要。

今後の予定（提案）
- strategy / execution / monitoring モジュールの実装（現在 __all__ で宣言済みだが詳細実装は未提供）。
- パフォーマンス改善（大規模データに対するクエリ最適化、並列化）。
- テストカバレッジの拡充（ユニット・統合テスト、モックを用いた外部 API テスト）。
- ドキュメント生成（API リファレンス、運用手順、ETL 定期実行方法）。

--- 

（この CHANGELOG はリポジトリ内のコード実装内容から推測して作成しています。運用上の正確なリリース日や追加の変更は実際のコミット履歴に基づいて更新してください。）