# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリのコードベースから推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased（今後の変更）
- 各バージョン（YYYY-MM-DD）: 主要な追加・変更・修正点を分類して記載

---

## [Unreleased]

（現時点では未公開の変更はありません）

---

## [0.1.0] - 2026-04-03

初回リリース。日本株向け自動売買・データ基盤・リサーチ用ユーティリティ群を含むパッケージを追加。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys パッケージの初期バージョン (src/kabusys/__init__.py, __version__ = "0.1.0")。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を優先順に読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パースの強化（コメント、`export KEY=val`、シングル/ダブルクォートとバックスラッシュエスケープの扱い、インラインコメント処理）。
  - .env 読み込み時に既存の OS 環境変数を保護する protected 機構（.env.local は上書き可能だが OS 変数は保護）。
  - Settings クラスで各種設定値をプロパティとして提供（J-Quants, kabuステーション, LINE, DB パス、監視閾値、環境モード、ログレベル判定 等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許可値以外は ValueError）。

- AI モジュール (src/kabusys/ai/)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC での変換を内部で扱う）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたりの記事数上限・文字数トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ処理。
    - レスポンスの厳密な JSON 検証とスコアのクリップ（±1.0）。
    - DuckDB 互換性考慮（executemany に対する空パラメータ回避、部分失敗時に既存スコアを保護する DELETE→INSERT 戦略）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM は gpt-4o-mini、OpenAI クライアントを生成して JSON レスポンスをパース。
    - ma200_ratio の算出や macro_sentiment の取得においてフェイルセーフを実装（データ不足や API エラー時は中立値 1.0 / 0.0 を使用）。
    - 計算結果は market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。失敗時はロールバックを試行し、ロールバック失敗をログ。

- リサーチ & ファクター (src/kabusys/research/)
  - factor_research (calc_momentum, calc_value, calc_volatility)
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR(20)・相対ATR、20日平均売買代金・出来高比率、PER/ROE を計算する関数群を提供。
    - DuckDB を用いた SQL ベースの実装。欠損やデータ不足時は None を返却する設計。
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
    - 将来リターン計算（デフォルトホライズン: 1,5,21 営業日）、IC（Spearman ρ）計算、統計サマリー、ランク付け関数を提供。
    - 外部依存（pandas 等）を排除した純 Python 実装。
  - research パッケージ初期エクスポートに zscore_normalize の再エクスポートを含む。

- データプラットフォーム / ETL (src/kabusys/data/)
  - calendar_management (マーケットカレンダー管理)
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB のデータがない/未登録場合は曜日ベースのフォールバックを使用。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に保存。バックフィル、健全性チェック（未来日チェック）を実装。
  - pipeline / etl
    - ETLResult データクラスを導入し ETL の取得/保存件数、品質問題、エラー情報を集約して返却。
    - pipeline モジュールの基本骨子を実装（差分取得、保存、品質チェックの呼び出し方針を含む）。
    - DuckDB テーブル存在判定等のユーティリティを提供。
  - jquants_client などの外部クライアント呼び出しを想定した設計（差分取得 → save_* 関数で冪等保存）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）  
  ただし各モジュールで次のような堅牢性対策を実装:
  - OpenAI API のリトライ/フェイルセーフ（API失敗時に中立スコアで続行）。
  - DuckDB の executemany 制約を回避するため、空パラメータでの実行を行わないガード。
  - DB トランザクションの失敗時に ROLLBACK を試行し、ロールバック失敗は警告ログ。

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キー等の機密情報は Settings を通じて環境変数で取得する設計。
- .env 自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テスト時に誤ったファイル読み込みを防止可能。

---

注記（設計上の重要なポイント）
- ルックアヘッドバイアス回避: news_nlp / regime_detector / research の関数は内部で datetime.today() や date.today() を直接参照せず、必ず引数で target_date を受け取る設計。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を patch して差し替え可能に実装。
- DuckDB 互換性や部分成功時のデータ保護（DELETE→INSERT によるコード絞り込み）を考慮。
- ロギングは各モジュールで適切に行われ、警告・例外時に状況を記録するよう配慮。

---

（この CHANGELOG はコード内容から推測して作成したものであり、実際のリリースノートは開発者の公式情報を優先してください。）