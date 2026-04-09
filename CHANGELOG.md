Keep a Changelog
全ての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

[0.1.0] - 2026-04-09
====================

Added
-----
- パッケージの初期リリース。
- 基本情報:
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数/設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して自動検出（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env ファイルの柔軟なパース実装:
    - export KEY=val 形式対応、コメント処理、クォート内のバックスラッシュエスケープ処理。
  - Settings クラスを提供し、アプリケーションで利用する各設定値をプロパティで取得可能:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB/SQLite）/監視設定/システム設定等。
    - 入力検証を実施（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
    - デフォルト値や Path.expanduser の処理を含む。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中リスクを監視し、既存保有比率が閾値を超えたセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告ログを出し 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
      - risk_based: リスク許容率と損切り幅から株数を算出。
      - equal/score: 重みと価格から配分を算出。
      - lot_size（単元株）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料/スリッページ見積）を考慮。
      - スケールダウン時は端数処理の再配分ロジックを実装し再現性を確保。

- 研究（Research）機能 (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。データ結合は DuckDB SQL で実行。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の妥当性チェックあり。
    - calc_ic: Spearman のランク相関（IC）を計算。データ不足や非有限値を除外し、3件未満なら None を返す。
    - rank: 同順位は平均ランクにするランク変換。浮動小数による ties の誤判定を防ぐため round(v, 12) を使用。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージ __all__ に zscore_normalize（kabusys.data.stats から）を含めて再エクスポート。

- AI 関連 (src/kabusys/ai/)
  - news_nlp:
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ保存するフローを実装。
    - 処理要点:
      - ニュースウィンドウ計算（JST 基準で前日 15:00～当日 08:30 を UTC に変換）。
      - 1銘柄あたりの記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - バッチ送信（_BATCH_SIZE=20）、JSON Mode を使用して厳密な JSON を期待。
      - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
      - レスポンスの厳密バリデーション（results リスト・code と score の存在・型検査・既知コードの照合）。スコアは ±1.0 にクリップ。
      - 書き込みは部分成功時に既存データを消さないよう、対象コードだけを DELETE → INSERT で置換（DuckDB の executemany の制約に配慮）。
    - テスト容易性: OpenAI 呼び出し関数をモック差し替え可能（_call_openai_api を patch）。

  - regime_detector:
    - ETF 1321（日経連動型）の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジームを判定（'bull'/'neutral'/'bear'）。
    - マクロニュースはタイトルをマクロキーワードでフィルタして取得し、LLM により macro_sentiment を算出。記事がない場合は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成の際はスコアを -1.0～1.0 にクリップし閾値でラベル付け。
    - DB への書き込みは冪等に行う（BEGIN/DELETE/INSERT/COMMIT）。OpenAI 呼び出しは独立実装でモジュール結合を抑制。
    - テスト容易性: OpenAI 呼び出し関数をモック差し替え可能。

- 監視データベース層 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を用いた永続化層を追加。init_monitoring_db により冪等で必要なテーブル・インデックス（system_status, trade_logs, positions, risk_logs 等）を作成。

- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。
  - 各サブモジュールの公開 API を __all__ に整備（portfolio, research, ai 等）。

Changed
-------
- N/A（このリリースは初期追加が主体）。

Fixed
-----
- DuckDB との互換性に配慮した実装:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を想定し、空の params を実行しないようガードを実装（news_nlp.score_news の DB 書き込み部分）。
- OpenAI API 呼び出しにおけるエラー処理とリトライの境界条件を明確化（429/ネットワーク/タイムアウト/5xx のみ再試行、それ以外は安全にスキップ）。

Deprecated
----------
- N/A

Removed
-------
- N/A

Security
--------
- 外部 API キー（OpenAI）は引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的に ValueError を発生させることで誤動作を防止。
- LLM レスポンスの不正な JSON や未知コードは無害化して無視するフェイルセーフな設計を採用。

Notes / 補足
------------
- 日付・時刻の扱いはルックアヘッドバイアスを避けるため、target_date ベースで計算し datetime.today()/date.today() を直接参照しない設計を徹底しています。
- AI 関連の実運用では OpenAI の利用制限やコスト、応答の信頼性に注意してください。デフォルトモデルは gpt-4o-mini に設定されていますが、運用に応じて変更可能です。
- 将来的な拡張点として、銘柄ごとの lot_size をマスタに持たせる等の TODO コメントがコード中に存在します。
- この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴がある場合はそちらを優先して参照してください。