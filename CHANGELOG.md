# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

一般方針:
- すべてのバージョンは安定した API/機能のスナップショットを示します。
- エントリは可能な限りコードベースから推測して記載しています。

## [0.1.0] - 2026-04-02

### 追加
- パッケージ初期リリース: kabusys（日本株自動売買システムの基礎ライブラリ）
  - パッケージメタ: src/kabusys/__init__.py にバージョン (0.1.0) と主要サブパッケージの公開一覧を定義。

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パースの強化:
    - コメント行・export プレフィックス対応。
    - シングル/ダブルクォート文字列のエスケープ処理に対応。
    - クォート無しでのインラインコメントの扱いの制御（直前が空白/タブであればコメントとみなす）。
  - 環境変数上書き処理（override / protected キーで OS 環境変数の保護）。
  - Settings クラスを提供し、以下のプロパティで設定を取得:
    - J-Quants / kabu ステーション / Slack / DB パス（duckdb/sqlite）/監視設定（PID ファイル・閾値）/システム環境（env, log_level）など。
  - 環境値検証:
    - KABUSYS_ENV（development/paper_trading/live の検証）。
    - LOG_LEVEL の有効値チェック。
    - 必須値未設定時は ValueError を送出するヘルパー _require。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）によりセンチメントを算出して ai_scores テーブルに書き込むワークフローを実装。
    - 時間ウィンドウ計算（JST ベース → DB は UTC 想定）を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄当たり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API レート制限・ネットワークエラー・サーバーエラー（5xx）のエクスポネンシャルバックオフによるリトライ実装。
    - レスポンスの厳密なバリデーションと復元（JSON パース失敗時に文字列から最外側の {} を抽出して再パースするフォールバック）。
    - スコアは ±1.0 にクリップ。
    - DuckDB の executemany に対する互換性考慮（空リストを渡さないチェック）。
    - フェイルセーフ: API エラー時は該当チャンクをスキップして処理継続（例外を必要以上に投げない）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - 計算手順:
      - DuckDB から過去 200 日分の終値を取得して ma200_ratio を計算（ルックアヘッドを防ぐため target_date 未満のみを使用）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得し OpenAI に投げて macro_sentiment を算出（記事無ければ LLM 呼び出しをスキップ）。
      - スコア合成・閾値評価により regime_label を決定し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しに関する堅牢性: 再試行・5xx の扱い・API タイムアウト等に対するフォールバック（失敗時 macro_sentiment=0.0）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データプラットフォーム関連 (kabusys.data)
  - ETL パイプライン
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート）。
    - 差分更新、バックフィル、品質チェックの設計を反映した骨組みを実装（jquants_client と quality モジュールを呼び出す想定）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装（互換性考慮の実装あり）。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を使った営業日判定・前後営業日探索・期間内営業日列挙のロジックを実装。
    - DB が未取得または該当日に登録がない場合の曜日ベースのフォールバック（週末を非営業日扱い）。
    - next_trading_day / prev_trading_day は最大探索日数制限を導入して無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィル・健全性チェック付き）を行う。

- 研究（Research）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）計算機能を実装。
    - DuckDB ベースの SQL と Python の組合せで実装。結果は (date, code) をキーとする dict のリストとして返却。
    - 関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）: calc_ic。
    - ランク変換ユーティリティ（同順位は平均ランク）: rank。
    - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

### 変更（設計・実装上の重要な決定）
- ルックアヘッドバイアス回避:
  - 全ての AI / 研究関数は datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB クエリは target_date 未満・LEAD/LAG の正しいウィンドウを使うことで未来情報参照を防止。

- OpenAI 呼び出しの設計:
  - gpt-4o-mini を想定し JSON Mode での応答をパースする設計。
  - news_nlp と regime_detector で API 呼び出し実装を分離（モジュール間でプライベート関数を共有しない）。

- データベース書き込みの冪等性:
  - ai_scores / market_regime 等への書き込みは DELETE → INSERT をトランザクション内で行い、部分失敗時に既存データを保護する方針。
  - DuckDB の仕様（executemany に空リストを渡せない）を考慮したガードを入れている。

- フェイルセーフポリシー:
  - 外部 API（OpenAI、J-Quants 等）失敗時には可能な限り処理を継続し、局所的にスキップまたはデフォルト値（例: macro_sentiment=0.0）を用いることで全体停止を回避する設計。

- ロギング / エラー処理:
  - 失敗・フォールバック時に詳細な logger.warning / logger.exception を出力し、呼び出し元での対応を容易にする設計。

### 修正（実装上の注意点・互換性対応）
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになる点を回避するため、空チェックを導入。
  - テーブル存在チェックや日付型の変換ユーティリティを用意。

- OpenAI レスポンスの頑強なパース:
  - JSON モードでも稀に余計なテキストが混ざるケースに備えて、最外側の波括弧を抽出して再パースするフォールバックを実装。

### 未実装 / 今後の拡張候補（コードから推測）
- 一部モジュール間のエクスポート調整（例: regime_detector の score_regime が ai パッケージの __all__ に含まれていない点の整理）。
- jquants_client / quality モジュールの具備（インターフェースを参照しているが実装は別途）。
- monitoring サブパッケージ（__init__ で公開予定だが本変更セットに実体は含まれていない可能性）。

---

注: 本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース目的・ドキュメントを基に調整してください。