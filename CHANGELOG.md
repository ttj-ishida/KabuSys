# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- （現時点の master に未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初回公開リリース。

### 追加 (Added)
- 基本パッケージ初期構成
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン __version__ = "0.1.0" とモジュール公開設定を含む。
  - 公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境設定/読み込み機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルート判定は .git または pyproject.toml を基準にして行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視設定 / システム設定（環境・ログレベル判定）などの設定プロパティを公開。必須項目は未設定時に ValueError を送出。

- AI ニュース解析（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメントスコアリング機能を実装。
  - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、バッチ（最大 20 銘柄/回）で LLM に送信してスコアを取得。
  - JSON Mode を利用した堅牢なレスポンス検証とパース処理を実装（余計な前後テキストの抽出処理含む）。
  - リトライロジック（429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフ）とフェイルセーフ（失敗時はそのチャンクをスキップ）を実装。
  - ai_scores テーブルへ冪等的に（DELETE → INSERT）スコアを書き込む処理を実装。部分失敗時に既存スコアを保護する設計。
  - タイムウィンドウ計算（JSTベースの前日15:00〜当日08:30相当）を calc_news_window 関数として実装。
  - 公開 API: score_news(conn, target_date, api_key=None) を提供。
  - テスト容易性のため OpenAI 呼び出し点は差し替え可能に実装（内部 _call_openai_api の patch を想定）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定する機能を実装。
  - prices_daily と raw_news を参照して ma200_ratio とマクロ記事タイトルを取得、OpenAI により macro_sentiment を算出、重み合成して regime_label を決定。
  - OpenAI 呼び出しは独立実装で、リトライや 5xx の扱いを含む堅牢化を実装。API 失敗時は macro_sentiment=0.0 のフォールバック。
  - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - 公開 API: score_regime(conn, target_date, api_key=None) を提供。
  - ルックアヘッドバイアス対策（date < target_date の排他条件等）を設計に反映。

- 研究（Research）モジュール（src/kabusys/research/）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）等のファクター計算を実装。
    - DuckDB 上で SQL を利用した高速計算実装。データ不足時の None ハンドリングあり。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns; 任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic; スピアマンのランク相関）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
  - research パッケージの __init__ で主要ユーティリティを再エクスポート。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定・前後営業日取得・範囲内営業日取得・SQ判定のロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバックを行う設計。最大探索日数制限で無限ループを回避。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ calendar_update_job を実装（バックフィル・健全性チェック・API 呼び出しの例外ハンドリング含む）。
  - ETL / pipeline:
    - ETL 実行結果を表すデータクラス ETLResult を追加（target_date, fetched/saved counts, quality issues, errors 等を保持、to_dict を提供）。
    - pipeline モジュールのインターフェース（ETLResult の再エクスポート）を提供。
    - ETL の設計方針として差分更新、バックフィル、品質チェック（quality モジュール経由での問題収集）および id_token 注入によるテスト容易性を文書化。

- その他ユーティリティ
  - data パッケージに calendar/jquants_client 等の参照用骨組み（実装は別モジュールを想定）。
  - ai モジュールで news_nlp.score_news をトップレベルでエクスポート。

### 変更 (Changed)
- （初回公開のため過去バージョンからの変更はありません）

### 修正 (Fixed)
- （初回公開のため修正履歴はありません）

### 削除 (Removed)
- （初回公開のため削除はありません）

### 非推奨 (Deprecated)
- （なし）

### セキュリティ (Security)
- OpenAI API キーを明示的に引数で渡せる設計とし、環境変数依存からの柔軟性を確保（テスト時の差し替えを容易化）。

---

注記:
- 全体設計において「ルックアヘッドバイアス防止」「DB への冪等書き込み」「外部 API のフェイルセーフ（継続）」「テスト容易性（差し替え可能な内部呼び出し）」といった方針が一貫して適用されています。
- DuckDB を主要なローカルデータベースとして想定しており、SQL + Python の組合せでパフォーマンスと可読性のバランスを取っています。