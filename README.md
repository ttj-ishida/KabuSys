# KabuSys

KabuSys は日本株向けの自動売買フレームワークの骨組みです。データ取得（data）、売買戦略（strategy）、注文実行（execution）、稼働監視（monitoring）という責務を分離したパッケージ構成になっており、独自のアルゴリズムや実行ロジックを実装して組み合わせることを想定しています。

現在は最小構成（パッケージの骨組み）の状態です。開発者が各モジュールを実装して拡張して利用します。

バージョン: 0.1.0

---

## 機能一覧（予定／想定）

- データ取得モジュール（data）
  - 市場データや板情報、過去値の収集
  - キャッシュ/永続化のインターフェース
- 売買戦略モジュール（strategy）
  - 売買シグナルの生成（テクニカル指標、マシンラーニングなど）
  - シグナルのフィルタリング／ポジション管理
- 注文実行モジュール（execution）
  - ブローカー／API への注文送信（成行・指値・取消し等）
  - 注文ステータス管理と再送ポリシー
- 稼働監視モジュール（monitoring）
  - ログ・メトリクス収集、アラート（メール／Slack 等）
  - システムヘルスチェック

---

## 要求環境

- Python 3.8+
- 開発用に仮想環境（venv / virtualenv 等）推奨
- 実際の API や依存ライブラリは各自で追加（例: requests、pandas、numpy、websocket-client 等）

---

## セットアップ手順

1. リポジトリをクローン
   - 例:
     git clone <リポジトリURL>
     cd <リポジトリ>

2. 仮想環境を作成して有効化
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 開発用インストール（編集しながら使う場合）
   - pip install -e .

4. 依存関係がある場合は requirements.txt を作成してから:
   - pip install -r requirements.txt

（現状のリポジトリは骨組みのみのため、追加の依存はありません）

---

## 使い方（基本）

まずパッケージのバージョン確認・基本インポートの例:

```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

各サブパッケージは以下のように参照します（サンプル）:

```python
from kabusys import data, strategy, execution, monitoring
```

各モジュールは現時点では空のパッケージです。一般的な利用フロー（サンプル実装の雛形）：

1. data パッケージに DataProvider を実装
2. strategy パッケージに Strategy クラスを作成し、DataProvider を使ってシグナル生成
3. execution パッケージに Executor を実装して注文を発行
4. monitoring パッケージでログやメトリクスを収集

雛形サンプル:

```python
# src/kabusys/data/provider.py
class DataProvider:
    def fetch_ohlcv(self, symbol, period):
        # 実装: API 呼び出しやファイル読み込み
        raise NotImplementedError

# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def __init__(self, data_provider):
        self.data = data_provider

    def generate_signal(self, symbol):
        # 実装: シグナル判定（例: 移動平均クロス）
        return "BUY"  # or "SELL" / "HOLD"

# src/kabusys/execution/executor.py
class Executor:
    def send_order(self, symbol, side, size):
        # 実装: 注文送信
        print(f"Send {side} order for {symbol}: {size}")

# 実行例
dp = DataProvider()
st = SimpleStrategy(dp)
ex = Executor()

signal = st.generate_signal("7203")  # トヨタの銘柄コードなど
if signal == "BUY":
    ex.send_order("7203", "BUY", 100)
```

---

## ディレクトリ構成

現在のプロジェクト構成（主要ファイル）:

- src/
  - kabusys/
    - __init__.py            # パッケージのメタ情報（__version__ など）
    - data/
      - __init__.py          # データ取得関連モジュールを配置
    - strategy/
      - __init__.py          # 戦略ロジックを配置
    - execution/
      - __init__.py          # 注文実行ロジックを配置
    - monitoring/
      - __init__.py          # 監視・ログ収集を配置

例:

- src/kabusys/__init__.py         (現在: __version__ = "0.1.0")
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発者向けメモ

- 拡張方針
  - 各サブパッケージに責務を限定してクラスや関数を追加してください（単一責任の原則）。
  - インターフェース（DataProvider、Strategy、Executor、Monitor など）を先に定義しておくと実装が容易になります。
- テスト
  - tests/ ディレクトリを作り、ユニットテストを追加してください（pytest 推奨）。
- ロギング
  - Python の logging モジュールを利用して、monitoring と連携できるログ出力を行ってください。
- 実運用時の注意
  - 注文実行ロジックにはネットワーク障害や二重注文を防ぐための堅牢なエラーハンドリングが必須です。
  - 本番環境では実際のブローカー API キーやシークレットは安全に管理してください（環境変数やシークレット管理サービスを利用）。

---

## 貢献・問い合わせ

- プルリクエスト歓迎（機能追加、バグ修正、ドキュメント改善）
- Issue を立てて議論してください
- コードスタイル: PEP8 準拠を推奨

---

必要であれば、README に具体的な使用例・依存関係・CI 設定（GitHub Actions 等）を追記できます。どの機能を最初に実装したいか教えてください。具体的な実装サンプルを作成して支援します。