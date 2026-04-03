CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------

（現状なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys
  - パッケージメタ情報を src/kabusys/__init__.py にて管理（__version__ = "0.1.0"）。
  - public サブパッケージ一覧を __all__ に宣言（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - .env の行パースは export 構文および引用符・エスケープ・インラインコメントに対応。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 既存 OS 環境変数を保護する protected オプションや override 挙動を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定をプロパティ経由で取得。
  - 設定値に対するバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と便利プロパティ（is_live / is_paper / is_dev）を実装。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management
    - market_calendar を元にした営業日判定（is_trading_day）、SQ判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を実装。DB の登録がない日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に保存。バックフィル、先読み、健全性チェックを実装。
  - pipeline / etl / ETLResult
    - ETL の結果を表す dataclass ETLResult を公開（取得数・保存数・品質問題・エラー集約）。
    - ETL パイプラインの設計に基づく差分取得・保存・品質チェックのためのユーティリティ群（jquants_client / quality 連携を想定）。
  - DuckDB を用いた DB 操作（トランザクション制御、BEGIN/COMMIT/ROLLBACK、executemany の空列表回避等の互換性対策を考慮）。

- AI（src/kabusys/ai/*）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースを組成し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を実装。
    - バッチ処理（銘柄 20 件／チャンク）、記事トリム（記事数上限・文字数上限）、JSON Mode のレスポンス検証、数値クリッピング、失敗時のフェイルセーフ（該当チャンクはスキップ）を実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をパッチ可能）。
    - タイムウィンドウの算出関数 calc_news_window（JST 時刻に基づく UTC 変換）を提供。

  - regime_detector.score_regime
    - ETF 1321（Nikkei ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を market_regime テーブルに冪等で書き込む実装。
    - マクロニュース抽出、LLM 呼び出し（gpt-4o-mini）、リトライ、レスポンスパースおよびフォールバック（API 失敗時 macro_sentiment=0.0）を備える。
    - ルックアヘッドバイアス対策として datetime.today() 等を参照しない設計（target_date 未満のデータのみ使用）。

- リサーチ（src/kabusys/research/*）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを算出。
    - momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時 None を返す）。
    - volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - value: PER（EPS が 0 または欠損時は None）、ROE（最新財務データの取得ロジック）。
  - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearman のランク相関による IC）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- 汎用設計上の配慮（クロスモジュール）
  - DuckDB ベースの SQL 処理でパフォーマンスと互換性を配慮（ウィンドウ関数、ROW_NUMBER、LEAD/LAG 等を利用）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定）し、トランザクションとロールバックを適切に扱う。
  - API レスポンスのバリデーションとクリッピングで安全側に倒す設計（無効応答や API 障害がアルゴリズム全体を停止させない）。
  - 外部依存（OpenAI, J-Quants など）の呼び出し失敗を考慮したフォールバックとログ出力。
  - ルックアヘッドバイアス防止のため、内部処理は target_date ベースで deterministic に動くよう設計。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）ただし以下の堅牢化が反映済み:
  - OpenAI API 呼び出しでの各種エラー（RateLimit, Connection, Timeout, APIError）に対するリトライ／フォールバックロジックを実装。
  - DuckDB の executemany に関する互換性問題（空パラメータの禁止）を回避するための事前チェックを追加。
  - market_calendar の NULL 値や未登録日の取り扱いに対する警告ログと安全なフォールバックを実装。

Security
- API キーの取り扱いは環境変数（OPENAI_API_KEY 等）に依存。キー未設定時は明確な ValueError を送出する設計。
- .env 自動読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Known limitations
- news_nlp の出力は strict JSON を期待するが、稀に前後に余分なテキストが混入することを想定して最外の {} を抽出する復元ロジックを備える。完全な保証はなし。
- calc_value では PBR や配当利回りは未実装（将来の拡張ポイント）。
- AI モデルは gpt-4o-mini を想定。将来のモデル差し替えは定数から変更可能。
- テスト戦略として OpenAI 呼び出し部分（_call_openai_api）のモック差し替えを前提にしている。
- パッケージ内に strategy / execution / monitoring の実装が想定されているが、今回提供されたスナップショットでは一部モジュールは実装ファイルが含まれていない可能性がある（__all__ により公開される構成を示唆）。

Acknowledgements
- 仕様・設計方針の多くはコメント（docstring）内に明示されており、ルックアヘッドバイアス回避、冪等性、フェイルセーフの方針が随所に見られます。

（この CHANGELOG はリポジトリ内の現行コードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。）