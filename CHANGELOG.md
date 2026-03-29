CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在の安定版に関するポリシー：  
- ここにはパッケージリリース（タグ付け）ごとの変更点を記載します。  
- 初回リリースは 0.1.0 として記載しています。

0.1.0 - 2026-03-29
-----------------

Added
- 新規パッケージ kabusys を追加（バージョン: 0.1.0）。
  - パッケージトップ: src/kabusys/__init__.py により main サブモジュール群を公開（data, strategy, execution, monitoring）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートを考慮した値抽出（バックスラッシュエスケープ対応）。
    - コメント処理（クォート内除外、非クォート時は '#' 前の空白でコメント判定）。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用）。
  - OS 環境変数を保護するための上書き制御（.env.local による上書きは可能だが OS 環境は保護）。
  - 必須環境変数取得用ヘルパー（_require）と Settings クラスを提供:
    - J-Quants, kabu API, Slack, DB パス等の設定プロパティを用意。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live / is_paper / is_dev のブール判定。
- AI 関連モジュールを追加（src/kabusys/ai/*）。
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信。
    - バッチサイズ・トリム制限（1銘柄あたり最大記事数 / 最大文字数）を導入してトークン肥大化を防止。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフ付きリトライ実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score 検証）とスコアの ±1.0 クリップ。
    - DuckDB への書き込みは冪等（DELETE → INSERT）かつ部分失敗時に既存データを保護する実装（executemany の空リスト問題への対応あり）。
    - calc_news_window により JST ベースの収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naïve datetime で算出。
    - API キーは引数で注入可能、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
    - テスト用に内部の OpenAI 呼び出し関数を patch で差し替え可能に設計。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出はキーワードベース、LLM（gpt-4o-mini）へ JSON モードで問い合わせ。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。リトライ/バックオフ実装あり。
    - レジームスコアは -1.0～1.0 にクリップし、判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止に配慮（target_date 未満のみ使用、datetime.today() を参照しない）。
- Research（src/kabusys/research/*）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility / Liquidity: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率等。
    - Value: raw_financials から最新財務を取得し PER・ROE を計算（EPS が 0/欠損の場合は None）。
    - 全て DuckDB SQL ベースで計算し、外部 API にはアクセスしない設計。
  - feature_exploration: calc_forward_returns（任意ホライズン対応）、calc_ic（Spearman ランク相関）、rank、factor_summary を実装。
    - calc_forward_returns: 指定の営業日ホライズンで LEAD を用いてリターンを算出、horizons のバリデーションあり。
    - calc_ic: factor と将来リターンを code で結合してスピアマン ρ を算出（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクとする実装（丸めで ties 検出精度を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出。
- Data レイヤ（src/kabusys/data/*）
  - calendar_management:
    - market_calendar テーブルの有無に応じた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（pipeline.ETLResult を etl 経由で再エクスポート）。
    - ETL パイプライン設計（差分更新、idempotent 保存、品質チェックの収集と継続処理）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日補正など）。
  - jquants_client 経由の fetch/save を想定した差分取得・保存フローを想定（実装は jquants_client に依存）。

Security
- 環境変数の取り扱い改善（OS 環境変数の保護、必須変数チェック）により誤設定の早期検出を実現。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 設計上の重要事項
- ルックアヘッドバイアス防止: AI モジュール・研究モジュールでは datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計。
- OpenAI API 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するが、不正な出力に対する復元ロジック（最外の {} を抽出）やパース失敗時のフェイルセーフ（スキップまたは 0.0）を備える。
- DuckDB の互換性考慮（executemany に空リストを渡さない等）を行っている。
- テスト容易性のため、内部の _call_openai_api 関数を unittest.mock.patch で差し替え可能に設計している箇所がある。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現段階では公開インターフェースのみ）。
- jquants_client の詳細実装との連携テスト、ETL の監査ログ強化。
- AI モジュールのプロンプト改善とモデル選択の柔軟化。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は、コミット履歴や PR の説明を参照して精査してください。