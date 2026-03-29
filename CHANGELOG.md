# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
各リリースはセマンティックバージョニングに従っています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買・リサーチ基盤のコア機能を実装しました。以下は主要な追加点と設計上の注記です。

### Added
- パッケージ基盤
  - kabusys パッケージ公開（__version__ = 0.1.0）。
  - パッケージ公開時に利用する主要サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 独自の .env 行パーサ実装（export プレフィックス、クォートやエスケープ、コメント処理に対応）。
  - 環境変数保護（OS 環境変数を上書きしないオプション）・上書きオプション実装。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得（J-Quants / kabu API / Slack / DB パス / 環境判定等）。
  - 環境のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出するスコアリング機能を実装。
  - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC として扱う calc_news_window）。
  - バッチ処理（1回に最大 20 銘柄）・記事数や文字数の上限（記事数上限、文字トリム）を実装しトークン肥大化を防止。
  - OpenAI 呼び出しの冗長対策：429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検査、未知コード無視、数値型チェック、スコアのクリップ）。
  - 書き込みは冪等に行う（対象コードのみを DELETE → INSERT して既存スコアを保護）。
  - テスト容易性のため _call_openai_api を patch 可能に実装。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
  - prices_daily / raw_news を参照し、レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - MA 計算・マクロニュース抽出・LLM 呼び出し（独立実装）・リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
  - ルックアヘッドバイアス防止の設計（date < target_date などの排他条件を採用）。

- データ関連（kabusys.data）
  - ETL インターフェース公開（ETLResult データクラスを pipeline モジュール経由で再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック、idempotent な保存処理を想定した ETLResult を実装。
    - DuckDB を前提とした日付最大取得やテーブル存在チェックなどのユーティリティを実装。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基に営業日判定・次/前営業日取得・期間内営業日取得・SQ 判定を提供。
    - DB にデータがない場合は曜日ベースでフォールバック（土日休み）。
    - カレンダー更新ジョブ（calendar_update_job）：J-Quants から差分取得 → 冪等保存、バックフィル、健全性チェックを実装。
    - 最大探索日数やバックフィル幅などの安全策を実装。

- リサーチ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）calc_momentum。
    - ボラティリティ・流動性（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）calc_volatility。
    - バリュー（PER, ROE）calc_value（raw_financials を参照、EPS=0 の扱いに注意）。
  - 特徴量探索ユーティリティ（feature_exploration）
    - 将来リターン計算（任意ホライズン、calc_forward_returns）。
    - IC（Information Coefficient／Spearman のランク相関）calc_ic。
    - ランク関数（同順位は平均ランク）および基礎統計量集計（factor_summary）。
  - データ正規化ユーティリティ（zscore_normalize）は kabusys.data.stats より利用可能として re-export。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

### Notes / Design decisions / Limitations
- すべての日付計算・データ参照はルックアヘッドバイアス対策として datetime.today()/date.today() に依存しない設計（外部から target_date を与える仕様）。
- OpenAI 呼び出しは JSON mode を使用し、レスポンスパースの失敗はスコア 0.0 などでフェイルセーフに処理する方針。
- DuckDB のバージョン差異に起因する制約（executemany に空リスト不可、リスト型バインドの挙動など）に対応するための回避ロジックを実装。
- 一部関数はデータ不足時に None を返す（例: ma200_dev、atr_20 など）。呼び出し側での取り扱いに注意が必要。
- OpenAI API キーは関数引数で注入可能（テスト容易化）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する。

### Testing / Extensibility
- OpenAI 呼び出し用の内部関数はテスト時に patch 可能（unittest.mock.patch の想定）。
- jquants_client 等の外部クライアントはデータ層で分離されており、ETL やカレンダー更新は外部依存の差分取得関数を通して動作する想定。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・統合テスト。
- ai モデルの切替やローカル置換対応の強化。
- 品質チェック（kabusys.data.quality）のルール追加と自動修復オプション。

（本 CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートとして公開する際は、リリース時の差分やマージ履歴に合わせて適宜更新してください。）