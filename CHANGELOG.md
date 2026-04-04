# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
この CHANGELOG は提供されたコードベースの内容から推測して作成した「初期リリース」向けの変更履歴です。

注意: バージョン番号はパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買・リサーチ基盤のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
- 設定・環境変数管理
  - 環境設定読み込みモジュール (kabusys.config)
    - プロジェクトルート検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み（.env → .env.local の優先順）。
    - 環境変数自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等。
    - 必須環境変数取得ヘルパー _require。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、LINE API、DB パス、監視設定、閾値、環境/ログレベル判定等）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）。
- AI ニュース / レジーム判定
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB クエリ）。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事上限・文字数上限でトークン肥大化対策。
    - JSON レスポンスの厳密バリデーションとフォールバック（出力が前後テキストを含む場合の {} 抽出処理）。
    - リトライ処理: レート制限 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行。
    - フェイルセーフ: API 失敗やパース失敗時は該当チャンクをスキップして処理継続。
    - 書き込み: ai_scores テーブルへ idempotent な置換（DELETE → INSERT）。部分失敗時に既存データを保護する設計。
    - テスト容易性のため、内部の OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - マクロセンチメントはニュースタイトルをマクロキーワードで抽出して LLM（gpt-4o-mini）で評価。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) により regime_score を算出し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 として継続。
    - ルックアヘッドバイアス回避設計（date < target_date の排他クエリ、datetime.today() を直接参照しない）。
- データプラットフォーム
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスの公開（ETL 実行結果の構造化、品質問題・エラーの集約、has_errors / has_quality_errors プロパティ、辞書変換メソッド）。
    - 差分更新・バックフィル・品質チェックを想定した ETL の設計方針（実装の骨子）。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定機能群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存（バックフィル・健全性チェックあり）。
    - 最大探索日数の設定や、無限ループ防止のための上限（_MAX_SEARCH_DAYS）。
  - jquants_client を前提としたデータ取得保存処理の呼び出し箇所（calendar_update_job 等）。
- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日 MA 乖離）。
    - ボラティリティ / 流動性: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率。
    - バリュー: PER（EPS に基づく）、ROE（raw_financials からの最新値結合）。
    - DuckDB SQL を活用した高効率なウィンドウ関数実装。
    - データ不足時の None 処理とログ出力。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンまでのリターン（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関によるファクター評価。データ不足時は None を返す。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median の算出。
    - rank ユーティリティ: 同順位は平均ランクを返す実装（丸め処理による tie 対応）。
  - デフォルトで外部依存（pandas 等）を用いず、標準ライブラリと DuckDB のみで実装。
- DB / テーブルの想定
  - コード全体で参照・書き込みを想定しているテーブル（例）:
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - DuckDB を前提とした SQL 実装（DuckDB の挙動やバージョンに配慮した実装上の注意点あり。例: executemany に空パラメータの回避）。

### 変更 (Changed)
- なし（初回リリースのため過去からの変更は無しと推定）

### 修正 (Fixed)
- なし（初回リリースのため過去からの修正は無しと推定）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし（ただし、OpenAI API キーおよび各種トークン等の管理は環境変数に依存。必須変数未設定時に ValueError を発生させる箇所あり。）

---

補足（実装上の注意点・運用上のガイドライン）:
- OpenAI API
  - API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げるため設定が必須（news_nlp.score_news / regime_detector.score_regime）。
  - 使用モデルは gpt-4o-mini。JSON Mode による厳密な JSON 出力を前提としているが、レスポンスパースの堅牢化処理あり。
- 環境変数 / .env
  - 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後の動作を考慮した実装（CWD に依存しない）。
  - OS 環境変数は protected として .env で上書きされない（.env.local は override=True で OS 環境の保護を保持）。
- ルックアヘッドバイアス対策
  - 分析 / スコアリング関数群は datetime.today()/date.today() を内部で直接参照しない設計。全て target_date ベースで動作するため再現性のあるバッチ処理が可能。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）失敗時は処理の継続を優先し、部分的な結果を残す方針（ただし致命的な DB 書き込み失敗は例外伝播）。

この CHANGELOG はコードベースから推測して作成したため、実際のリリースノートや運用手順についてはリポジトリの他ドキュメント（README / Design docs）と合わせて確認してください。