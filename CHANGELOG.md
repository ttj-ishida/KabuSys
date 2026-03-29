# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装・公開します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - パブリックモジュールとして data, strategy, execution, monitoring を公開。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント扱いの厳密化）。
  - 読み込み時の override / protected（OS環境変数保護）オプションを実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ
    - env / log_level のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを算出する score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window に実装。
    - バッチサイズ、記事数上限、文字数トリム、JSON Mode 応答のバリデーションなどの実践的設計。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - DuckDB 互換性考慮（executemany の空リスト回避等）を導入。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計（_call_openai_api のモック化想定）。
  - レジーム判定 (src/kabusys/ai/regime_detector.py)
    - 日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成するアルゴリズムを実装。
    - マクロニュースの抽出（マクロキーワード）と OpenAI への問い合わせ、リトライ処理、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。

- データ基盤 (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定 API を実装。
    - market_calendar テーブルの存在有無に応じた DB優先・曜日ベースフォールバックロジックを実装。
    - calendar_update_job により J-Quants からの差分取得と安全な保存（バックフィル・健全性チェック）を実装。
    - 検索上限日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却可能に。
    - 差分更新・バックフィル・品質チェックの設計方針に対応するユーティリティを実装。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などモメンタム系ファクター計算を実装。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率などボラティリティ・流動性指標を実装。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 算出（最新財務レコードの取得含む）。
    - DuckDB を用いた SQL ベース実装で、価格/財務データのみを参照する設計（実取引 API へはアクセスしない）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一括で計算するユーティリティを実装（可変ホライズン対応、入力バリデーション）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算する関数を実装（None や同値処理を考慮）。
    - rank: 同順位は平均ランクで扱うランク関数を実装（浮動小数の丸めで ties 処理の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算する関数を実装。
  - research パッケージの __all__ で主要関数を公開。

### 変更 (Changed)
- 初期実装のため該当なし（新規追加リリース）。

### 修正 (Fixed)
- 初期実装のため該当なし（新規追加リリース）。

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY に依存。キーの管理は運用で注意を要します（ライブラリ内での暗号化等の機構は未実装）。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス回避のため、日付判定やウィンドウ計算は外部から与えられる target_date に基づき行い、内部で date.today()/datetime.today() を参照しません。
- OpenAI 呼び出しはテスト性を考慮して差し替え可能（ユニットテストでのモック化が容易）。
- API 呼び出し失敗時は例外を直ちに上位へ投げずフェイルセーフ挙動（スコア 0.0 など）で継続する箇所があるため、運用での監視（ログ/アラート）を推奨します。
- DuckDB のバージョン依存に注意（executemany に空リストを渡せない等の互換性対応を含む）。
- .env パーサは POSIX 風の書式に広く対応するが、極端に非標準な .env の構文は保証対象外。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートや運用情報は、プロジェクトマネージャーやリリース担当者による確認・補足を推奨します。