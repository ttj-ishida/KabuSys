Keep a Changelog
=================

この変更履歴は「Keep a Changelog」フォーマットに準拠しています。  
初期リリースの内容は、コードベースから推測できる機能・設計方針・注意点をまとめたものです。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージの初期リリースを追加
  - パッケージ名: kabusys, バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py（__all__ に data, strategy, execution, monitoring を公開）

- 設定・環境変数管理
  - .env ファイルおよび環境変数から設定を読み込む utilities を実装（src/kabusys/config.py）。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を順に読み込む。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどをサポート。
  - Settings クラスを提供し、必須項目の取得時に明確なエラーを出力（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証を実装（有効値チェックと is_live/is_paper/is_dev の便宜プロパティ）。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）をサポート。

- データ基盤（Data）
  - ETL パイプライン基盤を実装（src/kabusys/data/pipeline.py）。
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分取得、バックフィル、品質チェックの枠組みとユーティリティ関数を含む。
    - DuckDB を用いた最大日付取得やテーブル存在チェックを実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を元にした営業日判定 API を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB データがない/不完全な場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新する夜間バッチ処理（バックフィルと健全性チェック付き）。
  - jquants_client との連携を想定した設計（fetch/save 関数を呼ぶ構造）。

- 研究（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新財務データを利用）。
    - DuckDB 上の SQL ウィンドウ関数を活用し、欠損・データ不足時の挙動（None 戻し）を明示。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 未満は None）。
    - rank, factor_summary: ランク変換（同順位は平均ランク）および基本統計量集計を提供。
  - research パッケージの __init__.py で主要関数を再エクスポートして利用しやすくしている。

- AI / NLP（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで問い合わせて銘柄別スコアを取得。
    - 出力は JSON Mode 想定で厳密な JSON を期待。レスポンスパースの耐性（前後の余計なテキストから {} 部分を抽出）を持つ。
    - バッチ化（最大 20 銘柄／回）、1銘柄あたり最大記事数と文字数制限（トリム）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで行い、非再試行エラーはスキップして継続。
    - 部分成功を考慮し、ai_scores テーブルへの書き込みは対象コードのみ DELETE → INSERT（トランザクション、部分失敗で既存スコアを保護）。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api を関数として分離し、patch で差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF（1321）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - calc_news_window を用いてニュースウィンドウを決定（news_nlp の window ロジックと整合）。
    - OpenAI 呼び出しは独立実装でモジュール間のプライベート関数共有を回避。リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 判定結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、DB 書込失敗時は ROLLBACK を試行して例外を伝播。

Changed
- （初回リリースのため、過去からの変更はなし）

Fixed
- （初回リリースのため、修正履歴はなし）

Notes / Design highlights
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定・ファクター計算のいずれでも内部で datetime.today() / date.today() を直接参照せず、関数呼び出し側から target_date を渡す設計。
  - DB クエリは target_date 未満／以前のデータを参照するように実装し、将来データ参照を防止。
- 耐障害性
  - OpenAI API 呼び出しに対してリトライ・バックオフを実装し、最終的な失敗は中立スコアまたはスキップでフェイルセーフに処理。
  - DB 書き込みはトランザクション／DELETE→INSERT の冪等パターンを採用。部分失敗時に既存データを不必要に消さない配慮あり。
- テスト容易性
  - OpenAI 呼び出しを行う内部関数を明示的に分離（_call_openai_api）しており、unit test で差し替え（patch）可能。
  - 多くの関数は引数で api_key や conn を注入可能で、外部依存を切り離しやすい。
- 依存と実行環境
  - DuckDB を前提に SQL 実行を行う実装。OpenAI の Python SDK（OpenAI）を使用する想定。
  - pandas 等の大きな依存を避け、標準ライブラリと DuckDB/OpenAI SDK による軽量実装。

Migration / Upgrade notes
- OpenAI API キーの供給方法が必須：score_news / score_regime を使う場合は api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
- 自動 .env 読み込みが不要な環境（CI/テスト等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを停止できます。
- DuckDB バージョン特性への対応: executemany に空リストを渡さない等の互換性考慮を実装。

Security
- 秘匿トークン（API キー等）は .env/.env.local か環境変数で管理する想定。.env.local は .env を上書きする優先度でロードされるが、OS 環境変数は保護される（.env 読み込み時に既存環境変数は上書きされない挙動を既定とし、.env.local 読み込み時でも OS 環境変数は保護）。

もし追加で
- リリース日を変更したい、
- 実際のリリースノート向けに各関数のスクリーンショットやサンプル出力を付けたい、
- あるいは英語版 CHANGELOG を併記したい
などご希望があればお知らせください。