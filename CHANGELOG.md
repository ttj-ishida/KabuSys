Keep a Changelog 形式の CHANGELOG.md（日本語）
※コードから推測して作成しています。実装やリリース日付は目安です。

Changelog
=========

すべての変更は "Keep a Changelog" の慣例に準拠して記載しています。  
フォーマットとセクションの意味については https://keepachangelog.com/ja/ を参照してください。

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース: kabusys 基本モジュール群を追加
  - src/kabusys/__init__.py: パッケージ公開とバージョン（0.1.0）。
- 環境設定読み込み機能
  - src/kabusys/config.py:
    - .env および .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先、.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
    - .env 行パーサ実装（export 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱い）。
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境・ログレベル検証等のプロパティ）。
    - 必須環境変数チェック用の _require ヘルパー。
- AI モジュール（LLM を用いたニュース解析・市場レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から記事を集約し、gpt-4o-mini（JSON mode）で銘柄別センチメントを算出して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当）を calc_news_window で提供。
    - バッチ処理（銘柄あたり最大 article/文字数制限、1回の API 呼び出しで最大 20 銘柄）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証とスコアクリップ（±1.0）。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。
  - src/kabusys/ai/regime_detector.py:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に冪等書き込み。
    - MA 計算、マクロキーワード抽出、OpenAI 呼び出し（gpt-4o-mini）、API エラー時は macro_sentiment=0.0 にフォールバック。
    - LLM 呼び出し関数は news_nlp 側と意図的に分離（モジュール結合を避ける）。
- Research モジュール（ファクター算出・特徴量解析）
  - src/kabusys/research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value を追加（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離の算出。データ不足時は None を返す設計。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率の算出。
    - Value: PER（EPS 不在・0 の場合は None）、ROE の取得。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関）、factor_summary、rank を提供。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。
  - src/kabusys/research/__init__.py: 主要関数を再エクスポート（zscore_normalize を含む）。
- Data / ETL / カレンダー
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job: J-Quants から差分取得し冪等保存（バックフィル、健全性チェック含む）。
    - DB 未登録日には曜日ベース（週末除外）のフォールバックを採用。
  - src/kabusys/data/pipeline.py:
    - ETLResult データクラスを中心とした ETL パイプライン用ユーティリティ（取得/保存件数、品質問題、エラー収集、has_errors / has_quality_errors / to_dict）。
    - jquants_client 経由の差分取得・保存と quality チェックの統合方針を明記。
  - src/kabusys/data/etl.py:
    - ETLResult の再エクスポート。
- テスト/デバッグ向けおよび運用配慮
  - DuckDB に関する互換性配慮（executemany に空リストを渡さないガード、日付の型変換ヘルパー等）。
  - 日付処理で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避、target_date パラメータ駆動）。
  - DB 書き込みは冪等性を確保（BEGIN/DELETE/INSERT/COMMIT や executemany を利用）。
  - OpenAI 呼び出し・レスポンスパースでの堅牢性（JSON 抽出ロジック、数値変換検証、未知コードの無視）。

Changed
- 初期リリースにつき過去との互換性変更はなし。

Fixed
- 初期リリースにつき修正履歴はなし。

Security
- 環境変数経由の API キー取扱い（OpenAI API キーの注入は引数か OPENAI_API_KEY 環境変数で行う設計）。
- 自動 .env ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Known issues / 注意点（コード解析に基づく推測）
- src/kabusys/data/pipeline.py の末尾付近に実装上の断片（return date.fro）が存在し、関数が未完であるように見えます。これはコードの切り取り・貼り付けミスまたは未実装の箇所と思われます。実運用前に該当箇所の修正（正しい日付変換ロジックの復元）を推奨します。
- OpenAI 呼び出し回りは gpt-4o-mini と JSON Mode を前提にしているため、OpenAI SDK のバージョン差分やモデル挙動変更に伴う調整が必要になる可能性があります。
- DuckDB のバインド挙動（特にリスト引数や executemany の空リスト制約）に依存した実装があるため、DuckDB の将来バージョンで互換性テストが必要です。

今後の予定（推測）
- pipeline._get_max_date の未完実装修正、ETL の差分算出ロジック完成。
- さらなる品質チェックルール追加（quality モジュール強化）。
- モデルやプロンプトのチューニング、LLM 呼び出しの抽象化（テスト容易性向上）。

ーーーーー

補足:
- 本 CHANGELOG は提供されたソースコードの内容を基に推測して作成しています。実際のコミット履歴・リリースノートと差異がある場合があります。必要があれば、リポジトリのコミットログやリリース日付に合わせて日付・項目を調整してください。