CHANGELOG
=========

すべてのプロジェクト変更点はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys/__init__.py にてパッケージのエクスポートを定義。

- 環境設定・読み込み機能を追加 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み挙動:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメントの扱いなどを考慮した独自パーサを実装。
    - OS 環境変数は保護（protected）され、.env.local は上書き（override=True）可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用フック）。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - 必須値取得用の _require を実装（未設定時は ValueError）。
    - プロパティ:
      - jquants_refresh_token, kabu_api_password, kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
      - slack_bot_token, slack_channel_id
      - duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
      - env（development/paper_trading/live の検証）
      - log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - is_live / is_paper / is_dev の便宜プロパティ

- ニュースNLP（AI）モジュールを追加 (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - score_news(conn, target_date, api_key=None)
    - 前日15:00 JST ～ 当日08:30 JST のニュースウィンドウを計算し、raw_news と news_symbols から銘柄ごとに記事を集約。
    - 銘柄ごとに最新最大 _MAX_ARTICLES_PER_STOCK 記事・文字数でトリムしたテキストを作成し、最大 _BATCH_SIZE (20) 銘柄ずつ OpenAI (gpt-4o-mini) にバッチ送信。
    - JSON Mode 応答のバリデーション、スコアの ±1.0 クリップ、部分成功を考慮した ai_scores テーブルへの冪等的書き換え（DELETE → INSERT）を実装。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため _call_openai_api を patch できるように設計。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計。
    - DuckDB 0.10 の executemany の制約を回避するため、空パラメータでの実行を避ける保護を実装。

- 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio の計算、マクロキーワードでフィルタしたニュース取得、OpenAI (gpt-4o-mini) によるセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 内部で使用する OpenAI 呼び出しは news_nlp と独立させ、モジュール結合を抑制。

- データ管理・カレンダー機能を追加 (src/kabusys/data/calendar_management.py)
  - JPX カレンダーの夜間バッチ更新 job (calendar_update_job) を実装（jquants_client に依存する差分取得/保存の呼び出し）。
  - 営業日判定ユーティリティ:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が存在しない場合は曜日（土日）ベースのフォールバックで判定。
    - DB データ優先・未登録日は曜日フォールバックの一貫した挙動。
    - 検索上限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル、健全性チェックを実装。

- ETL パイプラインを追加 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーの集約）。
  - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した設計。
  - jquants_client を用いた idempotent 保存（ON CONFLICT DO UPDATE）を前提にした設計。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- リサーチ／ファクター計算モジュールを追加 (src/kabusys/research/*)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算（価格との結合）。
    - DuckDB を用いた SQL + Python 実装、データ不足時は None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（LEAD を利用）。
    - calc_ic: スピアマン（ランク相関）による IC 計算（3 銘柄未満は None）。
    - rank: 同順位は平均ランクで処理（丸めで ties の検出漏れ対策）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - research パッケージ __init__ で主要関数をエクスポート。

- 汎用設計方針・実装上の注意点（ドキュメントに明記）
  - ルックアヘッドバイアスを避けるため、date 引数を明示的に受け、datetime.today()/date.today() を直接参照しない設計がプロジェクト全体で適用されていることを明記。
  - DuckDB を主要なローカル分析 DB として利用（互換性のための実装配慮あり）。
  - OpenAI API 呼び出しで JSON Mode を利用し、応答パースに冗長処理（pre/post の余計なテキスト抽出など）を組み込み堅牢化。
  - テスト容易性のため API 呼び出しラッパーを patch 可能にしている箇所あり（news_nlp._call_openai_api, regime_detector._call_openai_api 等）。
  - DB 書き込みは冪等設計（DELETE→INSERT や ON CONFLICT）で部分失敗時のデータ損失を最小化。
  - DuckDB 0.10 の executemany の制約を回避するため空パラメータを送らないガードを実装。

Security / Breaking Changes / Deprecated
- 初期リリースのため該当なし。
- 注意: 本バージョンでは OpenAI API キーや各種トークン（J-Quants, kabuステーション, Slack 等）を環境変数で扱う設計のため、取り扱いおよびデプロイ環境の機密管理に注意してください。

Known issues / TODO
- 一部モジュール（例: data.pipeline の実行フローや jquants_client 実装箇所）は外部クライアント実装に依存し、実稼働時は外部 API クライアントの実装・テストが必要。
- src/kabusys/data/pipeline._adjust_to_trading_day の実装スニペットが途中で切れているため、完全な挙動の確認が必要（今後の改善項目）。

---- 

注: 上記はコードベースの内容・ドキュメント文字列（docstring）から推測して作成した CHANGELOG です。実際のリリースノートとして利用する際は、追加の QA・変更差分の確認を推奨します。