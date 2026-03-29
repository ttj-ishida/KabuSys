# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初回リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パブリックモジュール: data, research, ai, ほか（__all__ に data, strategy, execution, monitoring を定義）

- 環境設定管理機能 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み:
    - プロジェクトルートを .git または pyproject.toml から検出して自動で .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護する protected オプションを実装（.env.local は override）。
  - 必須環境変数チェック用の _require ヘルパーと各プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
  - env 値とログレベルの検証（許容値のチェック: development / paper_trading / live など）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事数・文字数によるトリム、JSON Mode を利用したレスポンス検証。
    - 再試行 (指数バックオフ)・429/ネットワーク/タイムアウト/5xx に対応。
    - レスポンス検証とスコアクリッピング（±1.0）、DuckDB への冪等的な書き込み（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window 関数: JST ベースのニュース集計ウィンドウ計算（UTC naive datetime を返す）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はニュース NLP の窓計算を利用、OpenAI 呼び出しはモジュール内で独自実装。
    - API エラー時は macro_sentiment=0.0 としてフォールバック。
    - リトライ（最大 3 回）と指数的バックオフ対応。
    - ルックアヘッドバイアス防止設計（date 引数参照、datetime.today() を参照しない）。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離計算（データ不足時は None を返す）。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を取り出し PER/ROE を算出。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials のみ参照（本番発注には非依存）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対する fwd リターンを一括取得。
    - IC 計算（calc_ic）: スピアマンランク相関を実装（欠損・定数列ハンドリング）。
    - ランク関数（rank）: 同順位は平均ランク、丸めで ties の誤検出を防止。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの __all__ を整備（calc_momentum, calc_value, calc_volatility, zscore_normalize などをエクスポート）。

- Data モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理用ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルを優先し、未登録日は曜日ベースでフォールバック。最大探索日数制限（_MAX_SEARCH_DAYS）を導入。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーの収集と to_dict()）。
    - 差分取得・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
    - jquants_client を介した保存（save_*）関数を使用する想定。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

### 変更 (Changed)
- N/A（初回リリースのため履歴上の既存変更はなし）

### 修正 (Fixed)
- N/A（初回リリースのためバグ修正履歴はなし）

### 既知の仕様・設計上の注意点（ドキュメント的メモ）
- ルックアヘッドバイアス防止: 主要な処理は内部で datetime.today()/date.today() を直接参照せず、target_date 引数に依存する設計。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョンの挙動を考慮したガードを実装。
  - 一部 SQL で ROW_NUMBER / ウィンドウ関数を多用。
- OpenAI 関連:
  - デフォルトモデルは gpt-4o-mini。
  - JSON Mode（response_format）を利用して厳密な JSON を期待するが、前後余分なテキストが混ざる場合の復元処理を実装している。
  - テスト用に _call_openai_api の差し替えが可能。
- 環境変数の自動読み込みはプロジェクトルート検出に依存する（配布後の動作に配慮して実装）。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の保存を想定）。
- フェイルセーフ: 外部 API 失敗時は処理を継続し、安全なデフォルト（例: 0.0）でフォールバックする挙動が多く採用されている。

### セキュリティ (Security)
- API キーや機密情報は環境変数から取得する設計。必須キー未設定時は ValueError を送出して使用者に通知。
- .env ファイルの読み込みで OS 環境変数を保護する仕組み（protected set）を実装。

---

今後のリリースでは、strategy / execution / monitoring 関連の実装詳細、より細かな ETL 実行ロジック、テストカバレッジ、およびパフォーマンス改善（並列処理・キャッシュ等）に関する変更を追記する予定です。