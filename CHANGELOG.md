# CHANGELOG

すべての変更は Keep a Changelog に準拠しています。  
タグ付けはセマンティックバージョニングを使用しています。

## Unreleased
（なし）

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 基本パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - 公開サブパッケージ: data, strategy, execution, monitoring。
- 環境変数 / 設定管理モジュール（src/kabusys/config.py）
  - .env ファイル（.env/.env.local）および OS 環境変数から設定を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 自動ロードはパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を探索して行うため、CWD に依存しない実装。
  - .env パーサー実装（コメント・export 句・クォート中のエスケープ対応）。
  - Settings クラスを提供し、各種設定値（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル判定）をプロパティ経由で取得。
  - 必須変数未設定時に明示的なエラーを投げる _require 実装。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に、銘柄ごとのニュース集約 → OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出し ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ化（最大 20 銘柄/コール）、1 銘柄あたり記事数上限・文字数上限によるトリミング実装。
    - JSON Mode を用いたレスポンス検証・厳密パース（余分な前後テキストの修復処理含む）、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。フェイルセーフ: 失敗時は当該チャンクをスキップして継続。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）判定。
    - prices_daily からの MA200 比率計算、raw_news からマクロキーワードでの抽出、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - エラー時のフェイルセーフ（記事なしまたは API 失敗時は macro_sentiment=0.0）。
    - モジュール間の結合を避けるため、OpenAI 呼び出しは news_nlp と独立実装。
  - ai パッケージの公開関数: score_news を __all__ にて公開。
- Data / ETL / カレンダー（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを元に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録値優先、未登録日は曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分でカレンダーを取得し冪等保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを導入して ETL 実行結果（取得数/保存数/品質問題/エラー）を集約。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）の設計に対応する内部ユーティリティを実装。
    - jquants_client 経由でのデータ取得・保存を想定（差分取得・idempotent 保存）。
    - etl モジュールは ETLResult を再公開。
- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）計算を実装。
    - DuckDB 上の prices_daily / raw_financials を参照し外部 API 呼び出しは行わない設計。
    - データ不足時の None ハンドリング、出力は (date, code) キーを持つ dict リスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応、範囲検査と効率的な SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関を実装。必要レコード数チェック（>=3）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）を提供。
- 研究／AI／データ処理における共通設計上の注意点をドキュメント文字列で明示
  - ルックアヘッドバイアス防止（datetime.today()/date.today() への依存回避）。
  - DuckDB を用いたローカル分析基盤想定。
  - DB 書き込みは冪等を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK ハンドリング）。
  - テスト容易性（API 呼び出し差し替え、空返却時の安全な継続）を考慮。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### セキュリティ (Security)
- （初回リリースのため履歴なし）

---

注:
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット単位の履歴やバージョン管理履歴がある場合は、そちらに基づいて更新してください。