# KabuSys

KabuSys は日本株向けの自動売買（アルゴリズム取引）システムの骨組みを提供するPythonパッケージです。モジュール構成を通じてデータ取得、売買ロジック（ストラテジー）、注文実行、監視の責務を分離しており、各モジュールを実装・拡張することで自動売買システムを構築できます。

バージョン: 0.1.0

---

## 主な特徴
- モジュール分離
  - data: 市場データの取得・加工
  - strategy: トレード戦略の実装
  - execution: 注文の発行・管理（ブローカー接続）
  - monitoring: ログ記録・状態監視・アラート
- 軽量なパッケージ構造で拡張しやすい設計
- テスト／デバッグ用にローカルで動作させやすい骨組み

※ 現在のリポジトリは骨組み（スケルトン）であり、各モジュールの具体実装は含まれていません。これらを実装して使用します。

---

## 機能一覧（想定）
- 市場データの取得（リアルタイム／履歴）
- 指標の計算（移動平均、ボラティリティ等）
- 売買シグナル生成（シンプルなルールベースや機械学習）
- 注文の発行（成行、指値、約定管理）
- ポジション管理とリスク制御
- ログ・メトリクス出力、監視・アラート機能

---

## 動作要件（推奨）
- Python 3.8 以上
- 外部APIやブローカー接続を行う場合は各サービスのAPIキーや追加パッケージが必要

---

## セットアップ手順

1. リポジトリをクローン（ローカル開発用）
   ```
   git clone <リポジトリURL>
   cd <リポジトリフォルダ>
   ```

2. 仮想環境の作成と有効化（推奨）
   - venv を使う例:
     ```
     python3 -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 開発用に editable インストール:
     ```
     pip install -e .
     ```
   ※ 現状、必須の外部依存がない場合はこのステップは任意です。ブローカーAPIやデータ取得ライブラリを利用する場合は適宜追加してください。

---

## 使い方（簡単な例）

パッケージをインポートして使用する基本的な例（各モジュールは適宜実装が必要）:

```python
import kabusys

print("KabuSys version:", kabusys.__version__)

# モジュール群（骨組み）
from kabusys import data, strategy, execution, monitoring

# 例: データ取得
# df = data.get_history("7203.T", start="2023-01-01", end="2023-12-31")

# 例: ストラテジー定義（擬似コード）
# class MyStrategy(strategy.BaseStrategy):
#     def on_new_bar(self, bar):
#         signal = self.generate_signal(bar)
#         if signal == "BUY":
#             execution.place_order(symbol=bar.symbol, side="BUY", qty=100)
#
# 例: 実行・監視のフロー
# monitor = monitoring.Monitor()
# exec_engine = execution.Executor(api_key="...")
# strat = MyStrategy(executor=exec_engine, monitor=monitor)
# strat.run()
```

各モジュール（data, strategy, execution, monitoring）は現在パッケージに含まれているため、実装を追加するだけで統合できます。実装方針の例:

- data: データ取得関数（get_quote, get_history）やデータ加工ユーティリティを提供
- strategy: BaseStrategy クラスを定義し、サブクラスで on_new_bar / on_tick / on_start / on_stop 等を実装
- execution: ブローカーAPIラッパー（order, cancel, get_position）を実装
- monitoring: ログ出力、メトリクス収集、アラート送信を実装

---

## ディレクトリ構成

リポジトリ内の主要ファイル/フォルダ構成は以下のとおりです。

- src/
  - kabusys/
    - __init__.py            # パッケージ定義（バージョンと公開モジュール）
    - data/
      - __init__.py          # データ関連モジュール（未実装）
    - strategy/
      - __init__.py          # ストラテジー関連（未実装）
    - execution/
      - __init__.py          # 注文実行関連（未実装）
    - monitoring/
      - __init__.py          # 監視・ログ関連（未実装）
- README.md                 # 本ドキュメント

（現状各サブパッケージは空の __init__.py だけが配置されています。用途に応じてモジュールを追加してください。）

---

## 拡張のヒント / 実装ガイドライン
- インターフェースを明確にする
  - Strategy は入力（価格データ・イベント）と出力（注文シグナル）を明確に定義する
  - Execution は注文の非同期性・再試行や失敗時の挙動を考慮する
- テストを用意する
  - 履歴データを使ったバックテスト用ユーティリティを用意すると開発が早くなる
- ロギングとモニタリングを充実させる
  - 取引履歴、エラー、P&L を追跡し、アラート閾値を設定する
- セキュリティ
  - APIキー等の秘密情報は環境変数やシークレットマネージャで管理する

---

## 貢献
バグ修正、機能追加、ドキュメント改善は歓迎します。Pull Request の前に Issue を立てて相談してください。

---

## ライセンス
ライセンスは本リポジトリに明示されていません。配布・商用利用の前に適切なライセンスを追加してください。

---

質問や実装に関するサポートが必要であれば、どのモジュールをどのように実装したいかを教えてください。サンプル実装や設計例を提供します。