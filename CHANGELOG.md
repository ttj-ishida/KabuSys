# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、この CHANGELOG はリポジトリ内の現状のコードベースから推測して作成しています（初期リリース想定）。

## [0.1.0] - 2026-03-26

### 追加
- パッケージ初期リリース。
- 基本構成
  - パッケージメタ情報: kabusys/__init__.py にバージョン "0.1.0" と公開名前空間（data, strategy, execution, monitoring）を追加。
- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env の柔軟なパーサー実装（コメント行、export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメント処理等に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - 設定アクセス用の Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを定義）。
  - env と log_level の値検証を実装（許容値チェックとエラーメッセージ）。
- AI モジュール（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を利用して銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込む機能（score_news）。
    - バッチ処理（最大 20 銘柄 / コール）、1銘柄当たりの最大記事数・文字数トリム、スコア ±1.0 クリップ。
    - リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）実装。
    - レスポンス検証（JSON 抽出、results フィールド、code と score の妥当性チェック）を行い、不正レスポンスはスキップしてフェイルセーフに継続。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 _call_openai_api は patch 可能）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計。
  - regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ保存する機能（score_regime）。
    - ma200_ratio 計算（target_date より過去のデータのみ使用しデータ不足時は中立扱い）。
    - マクロ記事抽出（キーワードフィルタ）→ OpenAI でマクロセンチメントを評価（JSON モード）→ スコア合成。
    - API 障害時は macro_sentiment を 0.0 とするフォールバック、API 呼び出し部分はテスト差し替え可能。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。
- データ関連（kabusys.data）
  - calendar_management
    - JPX 市場カレンダー管理と営業日ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未登録の場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録値優先・未登録日は一貫して曜日ベースで補完。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得し保存、バックフィル・健全性チェックを含む）。
  - ETL / パイプライン（pipeline）
    - ETLResult データクラスを実装（ETL の取得件数／保存件数、品質問題リスト、エラー要約等を保持）。
    - ETLResult.to_dict により品質問題をシリアライズ可能。
    - jquants_client と quality モジュールを利用する想定の ETL 設計方針をコメントで明記。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。DuckDB の SQL を駆使して高速に集計。
    - 計算は prices_daily / raw_financials を参照し、データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。rank は同順位を平均ランクで扱う。
  - 研究用途向けユーティリティ（zscore_normalize）が data.stats から re-export される想定。
- ロギング
  - 各モジュールで詳細な debug/info/warning ログを出力するように実装（処理状況やフォールバック時の警告を含む）。
- テストしやすさと安全性
  - OpenAI 呼び出しやファイル読み込みのポイントで差し替え可能設計（単体テストでモックしやすい）。
  - ルックアヘッドバイアス対策：AI/研究モジュールは target_date を明示的に受け取り、現在時刻を直接参照しない。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 削除
- （初期リリースのため該当なし）

### セキュリティ
- （初期リリースのため該当なし）

---

注記:
- この CHANGELOG はコードベース（src/ 配下の実装）からの推測に基づいて作成しています。実際のリリースノート作成時は、コミット履歴や開発者コメントに基づいて追加情報（既知の制約、互換性、マイグレーション手順等）を反映してください。