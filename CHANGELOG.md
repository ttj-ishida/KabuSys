Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

フォーマット：
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)

Unreleased
---------

（現在未リリースの変更はここに記載）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開インターフェース:
    - src/kabusys/__init__.py によりサブモジュール data, strategy, execution, monitoring を公開。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / ロード機構 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出し、CWD に依存しない読み込みを実現。
  - .env パーサ実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等を考慮した堅牢なパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS 環境変数を保護する protected オプションを提供し、.env.local を用いた上書きロジックを実装。
  - 設定プロパティ:
    - J-Quants / kabuステーション / Slack / DB パス 等の取得用プロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許可値チェック）。
    - is_live/is_paper/is_dev 等のユーティリティプロパティ。

- AI ニュース解析モジュール (src/kabusys/ai/)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini / JSON Mode）でセンチメントを算出して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ定義（JST ベース → UTC に変換）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事トリム（文字数・記事数制限）を実装してトークン肥大を抑制。
    - API 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 部分失敗に備え、ai_scores 書き込みは該当コードのみ DELETE→INSERT する冪等的な更新を実装。
    - API キー未設定時は ValueError を送出。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ保存する機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウ抽出、LLM 呼び出しは専用実装で行いモジュール結合を最小化。
    - OpenAI 呼び出しはリトライや例外ハンドリングを実装し、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを搭載。
    - DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作を行い、失敗時は ROLLBACK を試みる。

- データプラットフォーム機能 (src/kabusys/data/)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装。
    - market_calendar が未取得の際は曜日ベースのフォールバック（週末は非営業日）を採用し、まばらな DB データに対しても一貫した結果を返す設計。
    - calendar_update_job により J-Quants API から差分取得 → 冪等保存（fetch/save の分離）を実装。バックフィルと健全性チェックを導入。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分更新・保存・品質チェックの流れを持つ ETL パイプラインの骨組みを実装。
    - ETLResult データクラスを実装して実行結果（取得数・保存数・品質問題・エラー）を構造化。
    - _get_max_date 等のユーティリティでテーブル存在チェックと最終日取得を提供。
    - デフォルトのバックフィル日数やカレンダー先読み日数等の設定を定義。
    - etl モジュールで pipeline.ETLResult を再エクスポート（公開インターフェース）。

- リサーチ / ファクタ計算 (src/kabusys/research/)
  - factor_research.py
    - momentum/value/volatility/liquidity などの定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - DuckDB を用いた SQL + Python により、prices_daily / raw_financials のみ参照して安全に計算。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマン (Spearman) ランク相関（IC）を実装（有効レコード 3 件未満で None）。
    - rank / factor_summary: ランク処理（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）の算出を実装。
    - 実装は外部ライブラリに依存せず、標準ライブラリのみで完結。

- 共通設計上の注意点・堅牢化
  - ルックアヘッドバイアス対策: 全ての処理で datetime.today() / date.today() を直接参照せず、target_date ベースでデータウィンドウを決定。
  - DuckDB を主要なローカル分析 DB として採用し、SQL のウィンドウ関数を活用。
  - OpenAI 呼び出し周りは JSON Mode を利用し、レスポンスのパース失敗時はフェイルセーフ（スコアを無視して継続）する方針。
  - DB 書き込みは原則冪等に設計（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗でも既存データを不必要に消さない工夫を実施。
  - ロギングを各モジュールに導入し、情報 / 警告 / 例外の追跡を容易に。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

注記
- OpenAI クライアント（OpenAI API）呼び出しは外部サービス依存のため、テストでは各モジュールの _call_openai_api をモックして動作確認する設計になっています。
- J-Quants / kabuAPI / Slack などの外部設定は環境変数で指定する必要があります（Settings の必須プロパティ参照）。