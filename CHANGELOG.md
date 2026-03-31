# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはまだ初期リリース段階です。日付はコードベースから推測可能な最新の日付を使用しています。

なお、本CHANGELOGはソースコードの実装内容から推定して作成しています。実際のコミット履歴ではなく、コードで提供されている公開API・挙動・設計方針に基づく要約です。

## [Unreleased]

- なし（初回リリースは 0.1.0 を参照）

## [0.1.0] - 2026-03-31

Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys（トップレベル __version__ = 0.1.0）
  - 公開モジュール一覧: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動的に読み込む仕組みを実装
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出（CWD に依存しない）
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS側環境変数を保護するため protected set を使用した上書き制御
  - .env の行パース機能を実装（コメント行、export プレフィックス、クォートとエスケープ、インラインコメント処理に対応）
  - 必須変数取得ヘルパー _require と、Settings クラスにより各種設定をプロパティで提供
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level 等）
    - 設定値のバリデーション（env 値・log_level 値の許容値チェック）
    - Path 型や float 変換を行うプロパティを用意

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから銘柄毎に記事集約し、OpenAI（gpt-4o-mini）のJSON modeでバッチ評価
    - タイムウィンドウ定義（JST 基準：前日 15:00 ～ 当日 08:30、DB には UTC で保存された datetime を期待）
    - バッチサイズ、記事数・文字数トリム（1銘柄あたり最大記事数・最大文字数）を導入してトークン肥大化を制御
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）や指数バックオフ実装
    - レスポンスバリデーション（JSON 抽出、results 配列、コード照合、スコア数値性、スコアクリップ ±1.0）
    - 部分成功に対応する安全な DB 書き込み戦略（取得したコードのみ DELETE → INSERT で置換）
    - テスト向けフック: _call_openai_api を patch で差し替え可能
    - 公開関数: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジームを判定
    - 処理フロー:
      - ma200_ratio を DuckDB の prices_daily から計算（target_date 未満のデータのみ使用、ルックアヘッド防止）
      - raw_news からマクロキーワードを用いて記事タイトルを抽出
      - OpenAI（gpt-4o-mini）でマクロセンチメントを評価（記事がない場合は LLM 呼び出しをスキップ）
      - API エラーやパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
      - スコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - リトライ方針、API エラーの分類（5xx はリトライ、その他は即座にフォールバック）を実装
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム / ETL（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）を扱うユーティリティを実装
    - 営業日判定、前後営業日取得、期間内営業日取得、SQ日判定を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日（平日）に基づくフォールバックを一貫して使用
    - 最大探索日数や健全性チェック、バックフィルのロジックを実装
    - カレンダー夜間更新ジョブ: calendar_update_job(conn, lookahead_days=90)（J-Quants API 経由で差分取得 → 保存）

  - pipeline / ETLResult（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（ETL の実行結果集約用）
      - 取得数 / 保存数 / quality_issues / errors / 補助プロパティ（has_errors / has_quality_errors）を提供
      - to_dict() で品質問題をシリアライズ可能
    - ETL モジュールは差分更新、バックフィル、品質チェックの方針を反映（実装はモジュール内に記述）

  - quality / jquants_client と連携する想定の設計方針（実際のクライアント実装は別モジュール）

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール
    - Momentum / Volatility / Value / Liquidity 等のファクター計算を実装
    - calc_momentum, calc_volatility, calc_value を提供
    - 移動平均（MA200）、ATR、出来高・売買代金の平均等を DuckDB 上の SQL とウィンドウ関数で計算
    - データ不足時の None ハンドリング、結果は (date, code) をキーとする dict リストで返却

  - feature_exploration モジュール
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）
    - ランク関数 rank（同順位は平均ランク）
    - ファクター統計 summary 関数 factor_summary（count/mean/std/min/max/median）
    - 外部ライブラリに依存せず純標準ライブラリ + DuckDB で実装

Changed
- 初期リリースとして、多くの内部設計方針やフェイルセーフ動作を文書化（docstring 内に設計方針を明記）
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）
  - DuckDB のバージョン制約（executemany の空リスト不可）に配慮した DB 書き込み実装
  - OpenAI 呼び出しはモジュール毎に独立した _call_openai_api を持ち、テストで差し替え可能にすることで結合を低減

Fixed
- 初期実装における下記の堅牢性向上を実施（コードに基づく推定）
  - .env 読み込みでファイルアクセス失敗時に警告を出して安全に継続
  - API 呼び出し失敗時は例外を上位に伝播させず、個別処理をスキップして他処理を継続するフェイルセーフを明示

Known limitations / Notes
- OpenAI API のモデルとして gpt-4o-mini を使用する想定でプロンプトは JSON mode を要求しているが、現実のレスポンスに対しては追加のパース耐性（前後余計なテキストの切り出し等）を持っている
- Slack / kabu ステーション等の外部実際の実行（execution / monitoring / strategy）の実装はこのスコープのコードからは確認できない（トップレベル __all__ に含まれるが該当ファイルは未提示）
- 一部モジュールは jquants_client / quality 等の外部依存モジュールを想定しており、その具象実装は別途必要
- ニュースの時間ウィンドウは JST ベースで定義され、DB 比較は UTC naive datetime を前提としているため時刻基準に注意が必要

---

作者注: この CHANGELOG は提供されたコードの内容から機能・設計方針・公開API を推定して作成しました。実際のリリースノートやコミット履歴とは差異がある可能性があります。必要があれば、実際の変更履歴に合わせて日付や項目を調整してください。